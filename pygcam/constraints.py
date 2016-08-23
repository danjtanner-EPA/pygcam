#! /usr/bin/env python
'''
Created on 4/26/15

@author: rjp
'''
import os

from .constants import LOCAL_XML_NAME
from .log import getLogger
from .query import readQueryResult, readCsv
from .utils import mkdirs, getBatchDir, getYearCols, printSeries

_logger = getLogger(__name__)

__version__ = "0.1"

PolicyChoices = ['tax', 'subsidy']
DefaultYears = '2020-2050'
DefaultCellulosicCoefficients = "2010:2.057,2015:2.057,2020:2.057,2025:2.039,2030:2.021,2035:2.003,2040:1.986,2045:1.968,2050:1.950,2055:1.932,2060:1.914"

# A list of these is inserted as {constraints} in the metaTemplate
_ConstraintTemplate = '                <constraint year="{year}">{value}</constraint>'

_MetaTemplate = '''<?xml version="1.0" encoding="UTF-8"?>
<scenario>
    <output-meta-data>
        <summary>
            This is a generated constraint file. Edits will be overwritten!
            {summary}
        </summary>
    </output-meta-data>
    <world>
        <region name="{region}">
            <{gcamPolicy} name="{name}">
                <market>{market}</market>
                {preConstraint}
{constraints}
           </{gcamPolicy}>
        </region>
    </world>
</scenario>
'''

DEFAULT_POLICY = 'policy-portfolio-standard'
DEFAULT_REGION = 'USA'
DEFAULT_MARKET = 'USA'

def generateConstraintXML(name, series, gcamPolicy=DEFAULT_POLICY, policyType=None,
                          region=DEFAULT_REGION, market=DEFAULT_MARKET,
                          preConstraint='', summary=''):

    def genConstraint(year):
        constraint = _ConstraintTemplate.format(year=year, value="{year%s}" % year)
        return constraint

    # Is this the most common case?
    if policyType and not preConstraint:
        preConstraint = '<policyType>{policyType}</policyType>'.format(policyType=policyType)

    constraints = map(genConstraint, series.index)
    constraintText = '\n'.join(constraints)

    template = _MetaTemplate.format(name=name, gcamPolicy=gcamPolicy, policyType=policyType,
                                    region=region, market=market, summary=summary,
                                    preConstraint=preConstraint, constraints=constraintText)

    args = {'year' + col: value for col, value in series.iteritems()}
    xml = template.format(**args)
    return xml


def saveConstraintFile(xml, dirname, constraintName, policyType, scenario, groupName=''): #, fromMCS=False):
    basename = '%s-%s' % (constraintName, policyType)
    constraintFile = basename + '-constraint.xml'       # TBD: document this naming convention
    policyFile     = basename + '.xml'

    dirname = os.path.join(dirname, scenario)
    mkdirs(dirname)

    pathname = os.path.join(dirname, constraintFile)
    _logger.debug("Generating constraint file: %s", pathname)
    with open(pathname, 'w') as f:
        f.write(xml)

    # compute relative location of local-xml directory
    # levels = 2
    # levels += 2 if fromMCS else 0
    # #levels += 1 if subdir else 0
    # localxml = '../' * levels + LOCAL_XML_NAME

    # TBD: test this
    prefix = '../../../' if groupName else '../../'
    localxml = prefix + LOCAL_XML_NAME

    # ToDo: replace subdir with groupDir?
    #source   = os.path.join(localxml, subdir, scenario, policyFile)
    source   = os.path.join(localxml, scenario, policyFile)
    linkname = os.path.join(dirname, policyFile)

    _logger.debug("Linking to: %s", source)
    if os.path.lexists(linkname):
        os.remove(linkname)
    os.symlink(source, linkname)

def parseStringPairs(argString, datatype=float):
    """
    Convert a string of comma-separated pairs of colon-delimited values to
    a pandas Series where the first value of each pair is the index name and
    the second value is a float, or the type given.
    """
    import pandas as pd

    pairs = argString.split(',')
    dataDict = {year:datatype(coef) for (year, coef) in map(lambda pair: pair.split(':'), pairs)}
    coefficients = pd.Series(data=dataDict)
    return coefficients

cellEtohConstraintTemplate ='''<?xml version="1.0" encoding="UTF-8"?>
<scenario>
  <output-meta-data>
    <summary>
      Cellulosic ethanol constraints.

      This is a generated constraint file. Edits will be overwritten!
    </summary>
  </output-meta-data>
  <world>
    <region name="USA">
      <policy-portfolio-standard name="cellulosic-etoh-{cellEtohPolicyType}">
        <policyType>{cellEtohPolicyType}</policyType>
        <market>USA</market>
        <min-price year="1975" fillout="1">-1e6</min-price>
        <constraint year="2020">{level2020}</constraint>
        <constraint year="2025">{level2025}</constraint>
        <constraint year="2030">{level2030}</constraint>
        <constraint year="2035">{level2035}</constraint>
        <constraint year="2040">{level2040}</constraint>
        <constraint year="2045">{level2045}</constraint>
        <constraint year="2050">{level2050}</constraint>
      </policy-portfolio-standard>
    </region>
  </world>
</scenario>
'''

US_REGION_QUERY = 'region in ["USA", "United States"]'

# TBD: make region an argument rather than assuming USA

def genBioConstraints(**kwargs):
    import pandas as pd

    #fromMCS = kwargs.get('fromMCS', False)
    resultsDir = kwargs['resultsDir']
    baseline = kwargs['baseline']
    policy = kwargs['policy']
    subdir = kwargs.get('subdir', '')
    defaultLevel = float(kwargs.get('defaultLevel', 0))
    annualLevels = kwargs.get('annualLevels', None)
    biomassPolicyType = kwargs['biomassPolicyType']
    purposeGrownPolicyType = kwargs['purposeGrownPolicyType']
    cellEtohPolicyType = kwargs['cellEtohPolicyType']
    coefficients = parseStringPairs(kwargs.get('coefficients', None) or DefaultCellulosicCoefficients)
    xmlOutputDir = kwargs['xmlOutputDir'] # required

    batchDir = getBatchDir(baseline, resultsDir)

    refinedLiquidsDF = readQueryResult(batchDir, baseline, 'Refined-liquids-production-by-technology')
    totalBiomassDF   = readQueryResult(batchDir, baseline, 'Total_biomass_consumption')
    purposeGrownDF   = readQueryResult(batchDir, baseline, 'Purpose-grown_biomass_production')

    yearCols = getYearCols(kwargs['years'])

    refinedLiquidsUSA = refinedLiquidsDF.query(US_REGION_QUERY)[yearCols]
    totalBiomassUSA   = totalBiomassDF.query(US_REGION_QUERY)[yearCols]
    purposeGrownUSA   = purposeGrownDF.query(US_REGION_QUERY)[yearCols]

    _logger.debug('totalBiomassUSA:\n', totalBiomassUSA)

    cellulosicEtOH  = refinedLiquidsUSA.query('technology == "cellulosic ethanol"')[yearCols]
    if cellulosicEtOH.shape[0] == 0:
        cellulosicEtOH = 0

    _logger.debug('cellulosicEtOH:\n', cellulosicEtOH)
    _logger.debug("Target cellulosic biofuel level %.2f EJ" % defaultLevel)

    desiredCellEtoh = pd.Series(data={year: defaultLevel for year in yearCols})
    if annualLevels:
        annuals = parseStringPairs(annualLevels)
        desiredCellEtoh[annuals.index] = annuals    # override any default values
        _logger.debug("Annual levels set to:", annualLevels)

    _logger.debug("Cell EtOH coefficients:\n", coefficients)

    # Calculate biomass required to meet required level
    deltaCellulose = (desiredCellEtoh - cellulosicEtOH) * coefficients
    _logger.debug('deltaCellulose:\n', deltaCellulose)

    biomassConstraint = totalBiomassUSA.iloc[0] + deltaCellulose.iloc[0]
    _logger.debug('biomassConstraint:\n', biomassConstraint)

    xml = generateConstraintXML('regional-biomass-constraint', biomassConstraint,
                                policyType=biomassPolicyType, summary='Regional biomass constraint.')
    saveConstraintFile(xml, xmlOutputDir, 'regional-biomass', biomassPolicyType, policy,
                       groupName=subdir)#, fromMCS=fromMCS)

    # For switchgrass, we generate a constraint file to adjust purpose-grown biomass
    # by the same amount as the total regional biomass, forcing the change to come from switchgrass.
    if kwargs.get('switchgrass', False):
        constraint = purposeGrownUSA.iloc[0] + deltaCellulose.iloc[0]
    else:
        constraint = purposeGrownUSA.iloc[0]

    xml = generateConstraintXML('purpose-grown-constraint', constraint, policyType=purposeGrownPolicyType,
                                summary='Purpose-grown biomass constraint.')
    saveConstraintFile(xml, xmlOutputDir, 'purpose-grown', purposeGrownPolicyType, policy,
                       groupName=subdir)#, fromMCS=fromMCS)

    # Create dictionary to use for template processing
    xmlArgs = {"level" + year : value for year, value in desiredCellEtoh.iteritems()}
    xmlArgs['cellEtohPolicyType'] = 'subsidy' if cellEtohPolicyType == 'subs' else cellEtohPolicyType

    xml = cellEtohConstraintTemplate.format(**xmlArgs)
    saveConstraintFile(xml, xmlOutputDir, 'cell-etoh', cellEtohPolicyType, policy,
                       groupName=subdir)#, fromMCS=fromMCS)


def bioMain(args):
    genBioConstraints(**vars(args))


yearConstraintTemplate = '''        <constraint year="{year}">{level}</constraint>'''

fuelConstraintTemplate ='''<?xml version="1.0" encoding="UTF-8"?>
<scenario>
  <output-meta-data>
    <summary>
      Define fuel constraints.
      This is a generated constraint file. Edits will be overwritten!
    </summary>
  </output-meta-data>
  <world>
    <region name="USA">
      <policy-portfolio-standard name="{fuelTag}-{fuelPolicyType}">
        <policyType>{fuelPolicyType}</policyType>
        <market>USA</market>
        <min-price year="1975" fillout="1">-1e6</min-price>
{yearConstraints}
      </policy-portfolio-standard>
    </region>
  </world>
</scenario>
'''

def genDeltaConstraints(**kwargs):
    import pandas as pd

    #fromMCS  = kwargs.get('fromMCS', False)
    baseline  = kwargs['baseline']
    policy    = kwargs['policy']
    groupName = kwargs.get('groupName', '')
    fuelTag   = kwargs.get('fuelTag')
    fuelName  = kwargs.get('fuelName')
    resultsDir  = kwargs['resultsDir']
    switchgrass = kwargs.get('switchgrass', False)
    defaultDelta = float(kwargs.get('defaultDelta', 0))
    coefficients = parseStringPairs(kwargs.get('coefficients', None) or DefaultCellulosicCoefficients)
    annualDeltas = kwargs.get('annualDeltas', None)
    xmlOutputDir = kwargs['xmlOutputDir'] # required
    fuelPolicyType = kwargs['fuelPolicyType']
    biomassPolicyType = kwargs.get('biomassPolicyType', None)
    purposeGrownPolicyType = kwargs.get('purposeGrownPolicyType', None)

    batchDir = getBatchDir(baseline, resultsDir)
    refinedLiquidsDF = readQueryResult(batchDir, baseline, 'Refined-liquids-production-by-technology')

    yearCols = getYearCols(kwargs['years'])
    #refinedLiquidsUSA = refinedLiquidsDF.query(US_REGION_QUERY)[yearCols]

    combinedQuery = US_REGION_QUERY + ' and technology == "%s"' % fuelName

    #fuelBaseline = refinedLiquidsUSA.query('technology == "%s"' % fuelName)[yearCols]
    fuelBaseline = refinedLiquidsDF.query(combinedQuery)[yearCols]
    if fuelBaseline.shape[0] == 0:
        fuelBaseline = 0
    else:
        _logger.debug('fuelBaseline:')
        printSeries(fuelBaseline, fuelTag)

    _logger.debug("Default fuel delta %.2f EJ", defaultDelta)

    deltas = pd.Series(data={year: defaultDelta for year in yearCols})
    if annualDeltas:
        annuals = parseStringPairs(annualDeltas)
        deltas.loc[annuals.index] = annuals    # override any default for the given years
        _logger.debug("Annual deltas: %s", deltas)

    # Calculate fuel target after applying deltas
    fuelTargets = fuelBaseline.iloc[0] + deltas
    _logger.debug('fuelTargets:\n')
    printSeries(fuelTargets, fuelTag)

    # Generate annual XML for <constraint year="{year}">{level}</constraint>
    yearConstraints = [yearConstraintTemplate.format(year=year, level=level) for year, level in fuelTargets.iteritems()]

    xmlArgs = {}
    xmlArgs['fuelPolicyType'] = fuelPolicyType
    xmlArgs['fuelTag'] = fuelTag
    xmlArgs['yearConstraints'] = '\n'.join(yearConstraints)

    xml = fuelConstraintTemplate.format(**xmlArgs)

    saveConstraintFile(xml, xmlOutputDir, fuelTag, fuelPolicyType, policy,
                       groupName=groupName)#, fromMCS=fromMCS)

    if switchgrass:
        # Calculate additional biomass required to meet required delta
        deltaCellulose = deltas * coefficients[yearCols]

        _logger.debug('\ndeltaCellulose:')
        printSeries(deltaCellulose, 'cellulose')

        totalBiomassDF = readQueryResult(batchDir, baseline, 'Total_biomass_consumption')
        totalBiomassUSA = totalBiomassDF.query(US_REGION_QUERY)[yearCols]

        biomassConstraint = totalBiomassUSA.iloc[0] + deltaCellulose.iloc[0]
        _logger.debug('biomassConstraint:')
        printSeries(biomassConstraint, 'regional-biomass')

        # For switchgrass, we generate a constraint file to adjust purpose-grown biomass
        # by the same amount as the total regional biomass, forcing the change to come from switchgrass.
        purposeGrownDF = readQueryResult(batchDir, baseline, 'Purpose-grown_biomass_production')

        # For some reason, purpose grown results are returned for 1990, 2005, then
        # 2020, 2025, but not 2010 or 2015. So we add any missing columns here.
        missingCols = list(set(yearCols) - set(purposeGrownDF.columns))
        if len(missingCols) > 0:
            purposeGrownDF = pd.concat([purposeGrownDF, pd.DataFrame(columns=missingCols)])

        purposeGrownDF.fillna(0, inplace=True)
        purposeGrownUSA  = purposeGrownDF.query(US_REGION_QUERY)[yearCols]

        xml = generateConstraintXML('regional-biomass-constraint', biomassConstraint, policyType=biomassPolicyType,
                                    summary='Regional biomass constraint.')

        saveConstraintFile(xml, xmlOutputDir, 'regional-biomass', biomassPolicyType, policy,
                           groupName=groupName)#, fromMCS=fromMCS)

        constraint = purposeGrownUSA.iloc[0] + deltaCellulose.iloc[0]

        xml = generateConstraintXML('purpose-grown-constraint', constraint,  policyType=purposeGrownPolicyType,
                                    summary='Purpose-grown biomass constraint.')

        saveConstraintFile(xml, xmlOutputDir, 'purpose-grown', purposeGrownPolicyType, policy,
                           groupName=groupName)#, fromMCS=fromMCS)
