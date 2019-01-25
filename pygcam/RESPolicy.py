#
# Goal is eventually to translate a file like ../etc/exampleRES.xml into standard GCAM XML.
#
from copy import deepcopy
import pandas as pd
from lxml import etree as ET
from lxml.etree import Element, SubElement
from .config import pathjoin, getParam
from .log import getLogger
from .XMLFile import XMLFile

_logger = getLogger(__name__)


# We deal only with one historical year (2010) and all future years
TIMESTEP = 5
LAST_HISTORICAL_YEAR = 2010
FIRST_MODELED_YEAR = LAST_HISTORICAL_YEAR + TIMESTEP
END_YEAR = 2100
GCAM_YEARS = [1975, 1990, 2005] + [year for year in range(LAST_HISTORICAL_YEAR, END_YEAR + 1, TIMESTEP)]

# Oddly, we must re-parse the XML to get the formatting right.
def write_xml(tree, filename):
    from io import StringIO

    parser = ET.XMLParser(remove_blank_text=True)
    xml = ET.tostring(tree.getroot())
    file_obj = StringIO(xml.decode('utf-8'))
    tree = ET.parse(file_obj, parser)

    tree.write(filename, pretty_print=True, xml_declaration=True)

# Surface level (tag and attribute) comparison of elements
def match_element(elt1, elt2):
    if elt1.tag != elt2.tag:
        return False

    attr1 = elt1.attrib
    attr2 = elt2.attrib

    if len(attr1) != len(attr2):
        return False

    try:
        for key, value in attr1.items():
            if value != attr2[key]:
                return False
    except KeyError:
        return False

    return True

def merge_element(parent, new_elt):
    """
    Add an element if none of parent's children has the same tag and attributes
    as element. If a match is found, add element's children to those of the
    matching element.
    """
    for sibling in parent:
        if match_element(new_elt, sibling):
            merge_elements(sibling, new_elt.getchildren())
            return

    # if it wasn't merged, append it to parent
    parent.append(deepcopy(new_elt))

def merge_elements(parent, elt_list):
    """
    Add each element in elt_list to parent if none of parent's children has the same tag
    and attributes as element. If a match is found, merge element's children with those
    of the matching element, recursively.
    """
    for elt in elt_list:
        merge_element(parent, elt)

def ElementWithText(tag, text, **kwargs):
    elt = Element(tag, **kwargs)
    elt.text = str(text)
    return elt

def SubElementWithText(parent, tag, text, **kwargs):
    elt = ElementWithText(tag, text, **kwargs)
    parent.append(elt)
    return elt

#
# Policy setup
#
def create_policy_region(region, commodity, market, consumer_elts, producer_elts,
                         minPrice=0, startYear=FIRST_MODELED_YEAR):
    policy_template =  """
    <policy-portfolio-standard name="{commodity}">
      <market>{market}</market>
      <policyType>RES</policyType>
      <constraint fillout="1" year="{startYear}">0</constraint>
    </policy-portfolio-standard>"""

    policy_elt = ET.XML(policy_template.format(commodity=commodity, market=market,
                                               minPrice=minPrice,
                                               startYear=startYear))
    if minPrice:
        SubElementWithText(policy_elt, 'min-price', minPrice, year=str(startYear))

    # Disable markets for the RECs prior to start year
    for year in GCAM_YEARS:
        if year < startYear:
            SubElementWithText(policy_elt, 'fixedTax', 0, year=str(year))
        else:
            break

    region_elt = Element('region', name=region)
    region_elt.append(policy_elt)
    region_elt.extend(consumer_elts)
    merge_elements(region_elt, producer_elts)

    return region_elt

def create_elt(tag, name, child_list):
    elt = Element(tag, name=name)
    elt.extend(deepcopy(child_list))    # since we reuse redundant elements
    return elt

def create_tech(tech, period_list, stub=True):
    tag = 'stub-technology' if stub else 'technology'
    return create_elt(tag, tech, period_list)

def create_subsector(subsector, tech_list):
    return create_elt('subsector', subsector, tech_list)

def create_sector(sector, subsector_list, pass_through=False):
    tag = 'pass-through-sector' if pass_through else 'supplysector'
    return create_elt(tag, sector, subsector_list)

#
# REC supply
#

def create_supply_period(year, commodity, outputRatio, pMultiplier):
    template = '''
<period year="{year}">
  <res-secondary-output name="{commodity}">
    <output-ratio>{outputRatio}</output-ratio>
    <pMultiplier>{pMultiplier}</pMultiplier>
  </res-secondary-output>
</period>'''

    xml = template.format(year=year, commodity=commodity,
                          outputRatio=outputRatio, pMultiplier=pMultiplier)
    elt = ET.XML(xml)
    return elt

def create_supply_sectors(df, commodity, targets, outputRatio=1, pMultiplier=1):
    sector_list = []

    for sector in df.sector.unique():
        sub_df = df[df.sector == sector]

        sub_list = []
        for subsector in sub_df.subsector.unique():
            tech_df = sub_df[sub_df.subsector == subsector]
            tech_list = []
            for tech in tech_df.technology.unique():
                period_list = []
                for year, coefficient in targets:
                    period = create_supply_period(year, commodity,
                                                  outputRatio=outputRatio,
                                                  pMultiplier=pMultiplier)
                    period_list.append(period)

                tech_list.append(create_tech(tech, period_list))

            sub_list.append(create_subsector(subsector, tech_list))

        sector_list.append(create_sector(sector, sub_list))

    return sector_list

#
# REC demand
#
def create_adjusted_coefficients(targets):
    """
    Create a dictionary of "adjusted-coefficient" elements (as XML text) for the given targets,
    where the key is the year and the value is the text for all elements starting at that year.
    """
    template = '<adjusted-coefficient year="{year}">{coefficient}</adjusted-coefficient>\n'

    # reverse a copy of the targets
    targets = sorted(targets, key=lambda tup: tup[0], reverse=True)  # sort by year, descending

    xml_dict = {}
    xml = ''

    for year, coefficient in targets:
        xml = template.format(year=year, coefficient=coefficient) + xml
        xml_dict[year] = xml

    return xml_dict

def create_demand_period(year, commodity, coefficients, priceUnitConv=0):
    template = '''
<period year="{year}">
  <minicam-energy-input name="{commodity}">
    {coefficients}
    <price-unit-conversion>{priceUnitConv}</price-unit-conversion>
  </minicam-energy-input>
</period>'''

    xml = template.format(year=year, commodity=commodity,
                          coefficients=coefficients, priceUnitConv=priceUnitConv)
    elt = ET.XML(xml)
    return elt

def create_demand_sectors(df, commodity, targets, priceUnitConv=0):
    sector_list = []

    coef_xml_dict = create_adjusted_coefficients(targets)

    for sector in df.sector.unique():
        sub_df = df[df.sector == sector]

        sub_list = []
        for subsector in sub_df.subsector.unique():
            tech_df = sub_df[sub_df.subsector == subsector]
            tech_list = []
            for tech in tech_df.technology.unique():
                period_list = []
                for year, coefficient in targets:
                    period = create_demand_period(year, commodity, coef_xml_dict[year],
                                                  priceUnitConv=priceUnitConv)
                    period_list.append(period)

                tech_list.append(create_tech(tech, period_list))

            sub_list.append(create_subsector(subsector, tech_list))

        sector_list.append(create_sector(sector, sub_list))

    return sector_list

def firstTarget(targets):
    """
    Return the first (year, coefficient) tuple in targets with coefficient != 0.
    """
    targets.sort(key=lambda tup: tup[0])    # sort by year

    for year, coefficient in targets:
        if coefficient: # ignore zeros
            return (year, coefficient)

def create_RES(tech_df, regions, market, commodity, targets,
               outputRatio=1, pMultiplier=1, priceUnitConv=0, minPrice=None):

    startYear, startTarget = firstTarget(targets)

    # Create "targets" with initial policy target in years prior to start year
    # since older plants will retain this as their definition (until GCAM is patched)
    prepolicy = [(year, startTarget) for year in GCAM_YEARS if year < startYear]

    targets = prepolicy + targets

    consumer_df = tech_df.query('consumer == 1')
    consumer_elts = create_demand_sectors(consumer_df, commodity, targets,
                                          priceUnitConv=priceUnitConv)

    producer_df = tech_df.query('producer == 1')
    producer_elts = create_supply_sectors(producer_df, commodity, targets,
                                          outputRatio=outputRatio, pMultiplier=pMultiplier)

    region_list = [create_policy_region(region, commodity, market,
                                        deepcopy(consumer_elts), deepcopy(producer_elts),
                                        startYear=startYear, minPrice=minPrice) for region in regions]
    scenario = Element('scenario')
    world = SubElement(scenario, 'world')
    merge_elements(world, region_list)

    return scenario

def match_str_or_regex(strings, name):
    import re

    if not name:
        return strings

    if name in strings:
        return [name]

    pattern = re.compile(name)
    matches = [s for s in strings if pattern.match(s)]
    return matches

def find_techs(tree, tups):
    """
    Return a list of (sector, subsector, technology) triads that occur in any of the
    indicated sectors and/or subsectors indicated in`pairs`. Each tuple in the list
    `pairs` must be also be the form (sector, subsector, technology), but in this case,
    each of these three element can be a string to match exactly items in the Global
    Technology Database with the same value for this attribute, or a regular expression.
    The value can also be `None` to match all values in the tech database for the given
    attributes. Thus, you can indicate all technologies in all subsectors of the 'electricity'
    sector as `('electricity', None, None)`, (or, equivalently, as `('electricity',)`), or
    all technologies whose name starts with "elec_" using a regex: `("^elec_.*",)`

    :param tree: (etree.ElementTree) in-memory representation of XML file
    :param tups: Tuples or lists of 1, 2, or 3 elements. If the tuple contains 1 element,
       is considered the sector, and the other elements are set to `None`. A 2-element
       tuple specifies sectors and subsectors, with technology set to `None`

    :return: (pandas.DataFrame) with three columns: sector, subsector, and technology,
      populated based on the given `tups`.
    """
    import re

    gtdb = tree.find('//global-technology-database')

    all_sectors = set(gtdb.xpath('./location-info/@sector-name'))
    tech_triads = []

    for tup in tups:
        tup = tup + (None, None, None)              # ensure length >= 3,
        sector, subsector, technology = tup[0:3]    # use first 3 elements

        sects = match_str_or_regex(all_sectors, sector)
        if not sects:
            _logger.warn("Sector name '{}' failed to match anything.".format(sector))
            continue

        for sect in sects:
            all_subsects = set(gtdb.xpath('./location-info[@sector-name="{}"]/@subsector-name'.format(sect)))

            subsects = match_str_or_regex(all_subsects, subsector)
            if not subsects:
                _logger.warn("In sector {}, subsector name '{}' failed to match anything.".format(sect, subsector))
                continue

            for subsect in subsects:
                locations = gtdb.xpath('./location-info[@sector-name="{}" and @subsector-name="{}"]'.format(sect, subsect))
                for location in locations:
                    # missing techs (with names above) => pass-through, so we ignore empty returns
                    all_techs = location.xpath('./technology/@name') + location.xpath('./intermittent-technology/@name')

                    matching_techs = match_str_or_regex(all_techs, technology)
                    for tech in matching_techs:
                        tech_triads += [(sect, subsect, tech)]

    return tech_triads

# TBD: create a library of functions that understand GCAM's XML

def get_tech_df(xmlfile, tech_specs):
    tree = XMLFile(xmlfile).getTree()
    tech_triads = find_techs(tree, tech_specs)

    tech_df = pd.DataFrame(data=tech_triads, columns=['sector', 'subsector', 'technology'])
    return tech_df

def get_electricity_tech_df():
    from pygcam.config import getParam, pathjoin

    tech_specs = [('electricity', None, None),
                  ('elect_td_bld', 'rooftop_pv', 'rooftop_pv'),
                  ('^elec_.*', None, None)]

    refWorkspace = getParam('GCAM.RefWorkspace')
    xmlfile = pathjoin(refWorkspace, 'input', 'gcamdata', 'xml', 'electricity_water.xml')

    tech_df = get_tech_df(xmlfile, tech_specs)
    tech_df.producer = 0
    tech_df.consumer = 0

    return tech_df

def set_actor(tech_df, tech_tups, actor, value=1):
    """
    actor must be 'producer' or 'consumer'
    """
    for tup in tech_tups:
        l = list(tup)

        sector    = l.pop(0)
        subsector = l.pop(0) if l else None
        tech      = l.pop(0) if l else None

        mask = (tech_df.sector == sector)
        if not any(mask):
            mask = tech_df.sector.str.contains(sector)

        if subsector:
            subsects = (tech_df.subsector == subsector)
            if not any(subsects):
                subsects = tech_df.subsector.str.contains(subsector)

            mask &= subsects

        if tech:
            techs = (tech_df.technology == tech)
            if not any(techs):
                techs = tech_df.technology.str.contains(tech)

            mask &= techs

        tech_df.loc[mask, actor] = value

def set_producers(tech_df, tech_tups):
    set_actor(tech_df, tech_tups, 'producer')

def set_consumers(tech_df, tech_tups):
    set_actor(tech_df, tech_tups, 'consumer')

def is_abspath(pathname):
    """Return True if pathname is an absolute pathname, else False."""
    import re
    return bool(re.match(r"^([/\\])|([a-zA-Z]:)", pathname))

def get_path(pathname, defaultDir):
    """Return pathname if it's an absolute pathname, otherwise return
       the path composed of pathname relative to the given defaultDir"""
    return pathname if is_abspath(pathname) else pathjoin(defaultDir, pathname)


class RECertificate(object):
    def __init__(self, node):
        self.elt = node
        self.name = node.get('name')
        self.targets   = self.parseTargets()
        self.producers = self.parseTechs('producers')
        self.consumers = self.parseTechs('consumers')

    def parseTargets(self):
        from .xmlEditor import expandYearRanges

        targetsNode = self.elt.find('targets')
        targetTups = [(t.get('years'), t.get('fraction')) for t in targetsNode.findall('target')]
        expanded = expandYearRanges(targetTups)
        return expanded

    def parseTechs(self, groupName):
        groupNode = self.elt.find(groupName)
        techs = groupNode.findall('tech')
        techTups = [(t.get('sector'), t.get('subsector'), t.get('technology')) for t in techs]
        return techTups

class RESPolicy(XMLFile):
    def __init__(self, filename):
        super(RESPolicy, self).__init__(filename, load=True, schemaPath='etc/RES-schema.xsd')

        self.root = root = self.tree.getroot()
        self.market  = root.get('market')
        self.regions = [s.strip() for s in root.get('regions').split(',')]
        self.certs = self.parseRES()

    def parseRES(self):
        certs = [RECertificate(cert) for cert in self.root.findall('certificate')]
        return certs

def resPolicyMain(args):
    import os
    from .error import CommandlineError
    from .utils import mkdirs

    scenario  = args.scenario
    inputXML  = args.inputXML  or getParam("GCAM.RESDescriptionXmlFile")
    outputXML = args.outputXML or getParam("GCAM.RESImplementationXmlFile")

    if not scenario and not (outputXML and is_abspath(outputXML)):
        raise CommandlineError("outputXML ({}) is not an absolute pathname; a scenario must be specified".format(outputXML))

    inPath   = get_path(inputXML,  pathjoin(getParam("GCAM.ProjectDir"), "etc", ))
    outPath  = get_path(outputXML, pathjoin(getParam("GCAM.SandboxRefWorkspace"), "local-xml", scenario))

    resPolicy = RESPolicy(inPath)

    # By default, all electricity techns consume RE certificates
    tech_df = get_electricity_tech_df()

    regions = resPolicy.regions
    market  = resPolicy.market

    scenario = None

    for cert in resPolicy.certs:
        targets = cert.targets
        commodity = cert.name

        # reset all to zero
        tech_df.consumer = tech_df.producer = 0

        # enable the indicated producers and consumers
        set_consumers(tech_df, cert.consumers)
        set_producers(tech_df, cert.producers)

        res = create_RES(tech_df, regions, market, commodity, targets)
        if scenario is None:
            scenario = res
        else:
            merge_elements(scenario, res.getchildren())

    tree = ET.ElementTree(scenario)
    mkdirs(os.path.dirname(outPath))    # ensure the location exists

    _logger.info("Writing '%s'", outPath)
    write_xml(tree, outPath)