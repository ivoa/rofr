<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                xmlns:oai="http://www.openarchives.org/OAI/2.0/"
                xmlns:vr="http://www.ivoa.net/xml/VOResource/v1.0"
                xmlns:vg="http://www.ivoa.net/xml/VORegistry/v1.0"
                xmlns:ri="http://www.ivoa.net/xml/RegistryInterface/v1.0"
                exclude-result-prefixes="vr vg ri oai xsi"
                version="1.0">

   <xsl:import href="testsVOResource.xsl"/>
   <xsl:import href="validationCommon.xsl"/>

   <xsl:output method="xml" encoding="UTF-8" indent="yes"
               omit-xml-declaration="yes" />

   <!--
     -  the harvesting verb/operation being tested.  Allowed values include, 
     -  Identify, ListRecords, ListMetadataPrefixes, ListSets
     -->
   <xsl:param name="queryType">[verb]</xsl:param>

   <!--
     -  the name for the query being tested.  (For diagnostic purposes)
     -->
   <xsl:param name="queryName">generic</xsl:param>

   <!--
     -  the input parameters (for diagnostic purposes)
     -->
   <xsl:param name="inputs"/>

   <!--
     -  the status values to show in the output.  The value should be 
     -  a space-delimited list of status values.  The default is to show
     -  all status types, e.g. "fail warn rec pass".  
     -->
   <xsl:param name="showStatus">fail warn rec pass</xsl:param>

   <!--
     -  the test codes to ignore.  The value should be a space-delimited
     -  list of test codes (i.e. "items") whose results should not be 
     -  returned.
     -->
   <xsl:param name="ignoreTests"/>

   <!--
     -  the baseURL used in this test
     -->
   <xsl:param name="baseurl"/>

   <!--
     -  the date and time for the execution of this validater.  This is used
     -  to ensure that stated dates are indeed in the past.
     -->
   <xsl:param name="rightnow">2007-02-24T14:49:50</xsl:param>

   <!--
     -  the IVOA identifier for the Registry being tested.  This is used
     -  by the ListRecords test to ensure that the Registry record is 
     -  included.  
     -->
   <xsl:param name="registryID">ivo://ivoa.net/sample</xsl:param>

   <!-- 
     -  if non-empty, check individual VOResource records 
     -->
   <xsl:param name="doVOResourceCheck">true</xsl:param>

   <!--
     -  if true, a record describing this Registry has been seen.  This 
     -  is set if ListRecords results in a resumption token.  
     -->
   <xsl:param name="seenRegistryRecord">false</xsl:param>

   <!--
     -  a slash-delimited list of authority IDs managed by this registry.
     -  This gets set as a result of an Identify test
     -->
   <xsl:param name="managedAuthorityIDs">//</xsl:param>

   <!--
     -  a unique, slash-delimited list of authority IDs that have appeared
     -  in VOResource records found thus far via ListRecords.  This will 
     -  be set if this test was invoked with a resumption token.
     -->
   <xsl:param name="foundAuthorityIDs">/</xsl:param>

   <!--
     -  a unique, slash-delimited list of authority IDs that have been 
     -  declared via Authority resource records retrieved via ListRecords.  
     -  This will be set if this test was invoked with a resumption token.
     -->
   <xsl:param name="declaredAuthorityIDs">/</xsl:param>

   <!--
     -  the name to give to the root element of the output results document
     -->
   <xsl:param name="resultsRootElement">RIHarvest</xsl:param>

   <!--
     -  this is the value of the showStatus parameter with spaces prepended 
     -  and appended to add processing by reportResult
     -->
   <xsl:variable name="verbosity">
      <xsl:value-of select="concat(' ',$showStatus,' ')"/>
   </xsl:variable>

   <!--
     -  this is the value of the show parameter with spaces prepended and 
     -  appended to add processing by reportResult
     -->
   <xsl:variable name="ignore">
      <xsl:value-of select="concat(' ',$ignoreTests,' ')"/>
   </xsl:variable>

   <!--
     -  We need to strip the trailing ? from the baseURL
     -->
   <xsl:variable name="thebaseurl">
      <xsl:choose>
         <xsl:when test="substring($baseurl,string-length($baseurl))='?'">
            <xsl:value-of 
                 select="substring($baseurl,1,string-length($baseurl)-1)"/>
         </xsl:when>
         <xsl:otherwise><xsl:value-of select="$baseurl"/></xsl:otherwise>
      </xsl:choose>
   </xsl:variable>

   <xsl:template match="/">
      <xsl:element name="{$resultsRootElement}">
         <xsl:attribute name="name">
            <xsl:value-of select="$queryName"/>
         </xsl:attribute>
         <xsl:attribute name="role">
            <xsl:value-of select="$queryType"/>
         </xsl:attribute>
         <xsl:if test="$inputs!=''">
            <xsl:attribute name="options">
               <xsl:value-of select="$inputs"/>
            </xsl:attribute>
         </xsl:if>
      
         <xsl:apply-templates select="/" mode="byquery"/>

      </xsl:element><xsl:text>
</xsl:text>
   </xsl:template>

   <xsl:template match="/" mode="byquery">

      <xsl:apply-templates select="oai:OAI-PMH/oai:Identify" mode="tests"/>
      <xsl:apply-templates select="oai:OAI-PMH/oai:ListMetadataFormats" 
                           mode="tests"/>
      <xsl:apply-templates select="oai:OAI-PMH/oai:ListSets" mode="tests"/>
      <xsl:apply-templates select="oai:OAI-PMH/oai:GetRecord" mode="tests">
         <xsl:with-param name="appelation">The Registry</xsl:with-param>
         <xsl:with-param name="chknotdeleted" select="true()"/>
      </xsl:apply-templates>
      <xsl:apply-templates select="oai:OAI-PMH/oai:ListRecords" mode="tests"/>

      <!-- check for error responses -->
      <xsl:call-template name="errorCheck">
         <xsl:with-param name="verb" select="$queryType"/>
      </xsl:call-template>

   </xsl:template>

   <!-- 
     -  check for error responses 
     -->
   <xsl:template name="errorCheck">
      <xsl:param name="verb"/>

      <xsl:variable name="stat">
         <xsl:copy-of select="not(oai:OAI-PMH/oai:error)"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">RI3.1.1</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="desc">
            <xsl:text>Service must respond to a legal OAI </xsl:text>
            <xsl:value-of select="$verb"/>
            <xsl:text> query</xsl:text>
            <xsl:if test="$verb='ListRecords' or $verb='GetRecord' or 
                          $verb='ListIdentifiers'">
               <xsl:text> (and support the 'ivo_vor' metadata prefix</xsl:text>
               <xsl:text> and the 'ivo_managed' set)</xsl:text>
            </xsl:if>
            <xsl:text>.</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <!--
     -  test the ListRecords verb assuming the use of the ivo_managed set
     -->
   <xsl:template match="oai:ListRecords" mode="tests">

      <xsl:variable name="foundAuthIDs">
         <xsl:call-template name="collectAuthIDs"/>
      </xsl:variable>
      <xsl:attribute name="foundAuthIDs">
         <xsl:value-of select="$foundAuthIDs"/>
      </xsl:attribute>

      <xsl:variable name="declAuthIDs">
         <xsl:call-template name="findAuthRecs"/>
      </xsl:variable>
      <xsl:attribute name="declAuthIDs">
         <xsl:value-of select="$declAuthIDs"/>
      </xsl:attribute>

      <!-- See if there is a resumption token -->
      <xsl:if test="oai:resumptionToken">
         <xsl:attribute name="resumptionToken">
            <xsl:value-of select="oai:resumptionToken[1]"/>
         </xsl:attribute>
      </xsl:if>

      <!-- record the presence of the Registry Record -->
      <xsl:if test="$seenRegistryRecord='true' or 
            oai:record/oai:metadata/ri:Resource[contains(@xsi:type,':Registry') 
                                                and identifier=$registryID]">
         <xsl:attribute name="seenRegistryRec">true</xsl:attribute>
      </xsl:if>

      <!-- make sure we have at least one record -->
      <xsl:call-template name="RI3.1.2a"/>

      <!-- make sure we have only ivo_vor Resource records -->
      <xsl:call-template name="RI3.1.2b"/>

      <!-- make sure the OAI identifiers match the VOResource identifiers -->
      <xsl:apply-templates select="." mode="RI3.1.3"/>

      <xsl:text>
</xsl:text>

      <xsl:if test="not(oai:resumptionToken) or 
                    normalize-space(oai:resumptionToken)=''">
         <!-- make sure the Registry record is included -->
         <xsl:call-template name="RI3.1.4a"/>

         <!-- make sure all necessary Authority records are included -->
         <xsl:call-template name="RI3.1.4c">
            <xsl:with-param name="authids" select="$foundAuthIDs"/>
            <xsl:with-param name="authrecs" select="$declAuthIDs"/>
         </xsl:call-template>
      </xsl:if>

      <!-- check each record -->
      <xsl:apply-templates select="oai:record" mode="ListRecords"/>
                          
      <!-- make sure there is an associated Authority record for this record -->
   </xsl:template>

   <!--
     -  make sure we have at least one record to prove we support the 
     -  ivo_vor metadata format
     -->
   <xsl:template name="RI3.1.2a">
      <xsl:variable name="stat">
         <xsl:copy-of select="boolean(oai:record/oai:metadata/*/identifier) and
                              boolean(oai:record/oai:metadata/*/curation)"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">RI3.1.2a</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="desc">
            <xsl:text>A Harvesting Registry must return VOResource </xsl:text>
            <xsl:text>records when metadataPrefix=ivo_vor.</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <!--
     -  make sure we have only ri:Resource records with ivo_vor
     -->
   <xsl:template name="RI3.1.2b">
      <xsl:variable name="stat">
         <xsl:copy-of select="count(oai:record/oai:metadata/*[not(self::ri:Resource)])=0"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">RI3.1.2b</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="desc">
            <xsl:text>When metadataPrefix=ivo_vor, each VOResource </xsl:text>
            <xsl:text>must be wrapped in a ri:Resource element.</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <!--
     -  test each record returned by ListRecords
     -->
   <xsl:template match="oai:record" mode="ListRecords">
      <xsl:param name="authids" select="'//'"/>
      <xsl:param name="authrecs" select="'//'"/>

      <xsl:if test="$doVOResourceCheck!=''">
         <xsl:text>
    </xsl:text>
         <VOResourceCheck ivo-id="{oai:header/oai:identifier}" 
                          status="{oai:metadata/ri:Resource/@status}"><xsl:text>
</xsl:text>

         <!-- make sure the OAI identifier matches the VOResource identifier -->
         <xsl:call-template name="RI3.1.3"/>

         <!-- make sure the OAI deleted records have no resource elements -->
         <xsl:call-template name="OAI2.5.1"/>

         <!-- validate the VOResource record -->
         <xsl:apply-templates select="oai:metadata/ri:Resource" 
                              mode="ListRecords"/>

         <xsl:text>    </xsl:text>
         </VOResourceCheck><xsl:text>
</xsl:text>
      </xsl:if>
   </xsl:template>

   <!--
     -  validate a VOResource record in the context of a ListRecords query
     -->
   <xsl:template match="ri:Resource" mode="ListRecords">
      <xsl:param name="authids" select="'//'"/>
      <xsl:param name="authrecs" select="'//'"/>

      <xsl:variable name="authid">
         <xsl:call-template name="getAuthorityID">
            <xsl:with-param name="id" select="identifier"/>
         </xsl:call-template>
      </xsl:variable>

      <!-- make sure the authority id is listed in the registry record -->
      <xsl:if test="@status!='deleted'">
         <xsl:call-template name="RI3.1.4b">
            <xsl:with-param name="authid" select="$authid"/>
         </xsl:call-template>
      </xsl:if>

      <!-- apply the general VOResource checks -->
      <xsl:apply-templates select="." mode="validateResource"/>
   </xsl:template>

   <!--
     -  return the authority ID portion from an IVOA identifier
     -->
   <xsl:template name="getAuthorityID">
      <xsl:param name="id"/>
      <xsl:variable name="noscheme" select="substring-after($id,'ivo://')"/>

      <xsl:choose>
         <xsl:when test="contains($noscheme,'/')">
            <xsl:value-of select="substring-before($noscheme,'/')"/>
         </xsl:when>
         <xsl:otherwise>
            <xsl:value-of select="$noscheme"/>
         </xsl:otherwise>
      </xsl:choose>
   </xsl:template>

   <!-- 
     -  make sure the OAI identifier matches the VOResource identifier 
     -->
   <xsl:template match="oai:ListRecords" mode="RI3.1.3">
      <xsl:variable name="nrecords" select="count(oai:record[oai:metadata/ri:Resource])"/>
      <xsl:variable name="nmatches"
                    select="count(oai:record[oai:header/oai:identifier =
                                  oai:metadata/ri:Resource/identifier])"/>
      <xsl:variable name="stat" select="$nrecords=$nmatches"/>

      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">RI3.1.3</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="desc">
            <xsl:text>The OAI record/header/identifiers must match </xsl:text>
            <xsl:text>the VOResource identifier (</xsl:text>
            <xsl:value-of select="$nmatches"/>
            <xsl:text> out of </xsl:text>
            <xsl:value-of select="$nrecords"/>
            <xsl:text> match).</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <!-- 
     -  make sure the OAI identifier matches the VOResource identifier 
     -->
   <xsl:template name="RI3.1.3">
      <xsl:variable name="stat">
         <xsl:copy-of select="oai:header/oai:identifier =
                                  oai:metadata/ri:Resource/identifier or oai:header/@status='deleted'"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">RI3.1.3</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="desc">
            <xsl:text>The OAI record/header/identifier (</xsl:text>
            <xsl:value-of select="oai:header/oai:identifier"/>
            <xsl:text>) must match the VOResource identifer (</xsl:text>
            <xsl:value-of select="oai:metadata/ri:Resource/identifier"/>
            <xsl:text>).</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <!-- 
     -   A record specified as deleted in the OAI header must not
     -   contain an OAI metadata element.
     -->
   <xsl:template name="OAI2.5.1">
      <xsl:variable name="stat">
         <xsl:copy-of select="oai:header/@status!='deleted' or
         oai:header[not(@status)] or count(oai:metadata/ri:Resource)=0"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">OAI2.5.1</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="desc">
            <xsl:text>An OAI record with status deleted </xsl:text>
            <xsl:text>may not contain a resource document. </xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <!--
     -  make sure the Registry record is included 
     -->
   <xsl:template name="RI3.1.4a">
      <xsl:variable name="stat">
         <xsl:copy-of 
    select="$seenRegistryRecord='true' or 
            boolean(oai:record/oai:metadata/ri:Resource[contains(@xsi:type,
                                                                 ':Registry') 
                                                 and identifier=$registryID])"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">RI3.1.4a</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="desc">
           <xsl:text>ListRecords must include the record for the </xsl:text>
           <xsl:text>registry being tested (</xsl:text>
           <xsl:value-of select="$registryID"/>
           <xsl:text>).</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <!-- 
     -  make sure there is an associated Authority record for every authority
     -  ID found
     -->
   <xsl:template name="RI3.1.4c">
      <xsl:param name="authids" select="'//'"/>
      <xsl:param name="authrecs" select="'//'"/>

      <xsl:call-template name="checkForAuthRec">
         <xsl:with-param name="next" select="substring($authids,2)"/>
         <xsl:with-param name="authrecs" select="$authrecs"/>
      </xsl:call-template>
   </xsl:template>

   <xsl:template name="checkForAuthRec">
      <xsl:param name="next" select="'/'"/>
      <xsl:param name="authrecs" select="'//'"/>

      <xsl:variable name="authid">
         <xsl:text>/</xsl:text>
         <xsl:value-of select="substring-before($next,'/')"/>
         <xsl:text>/</xsl:text>
      </xsl:variable>

      <xsl:if test="string-length($authid) > 2">
         <xsl:variable name="stat">
            <xsl:copy-of select="contains($authrecs,$authid)"/>
         </xsl:variable>
         <xsl:call-template name="reportResult">
            <xsl:with-param name="item">RI3.1.4c</xsl:with-param>
            <xsl:with-param name="status" select="$stat"/>
            <xsl:with-param name="desc">
               <xsl:text>ListRecords must include an Authority record </xsl:text>
               <xsl:text>for all authority IDs (including </xsl:text>
               <xsl:value-of 
                   select="substring-before(substring-after($authid,'/'),'/')"/>
               <xsl:text>).</xsl:text>
            </xsl:with-param>
         </xsl:call-template>

         <xsl:call-template name="checkForAuthRec">
            <xsl:with-param name="next" select="substring-after($next,'/')"/>
            <xsl:with-param name="authrecs" select="$authrecs"/>
         </xsl:call-template>
      </xsl:if>
   </xsl:template>      


   <xsl:template match="oai:Identify" mode="tests">

      <!-- grab the registry identifier off the top of the bat and save it
           as an attribute -->
      <xsl:for-each select="oai:description/ri:Resource[contains(@xsi:type,
                                                                 ':Registry')]">
         <xsl:if test="position()=1">
            <xsl:attribute name="regid">
               <xsl:value-of select="identifier"/>
            </xsl:attribute>

            <xsl:attribute name="manAuthIDs">
               <xsl:call-template name="catvals">
                  <xsl:with-param name="to">/</xsl:with-param>
                  <xsl:with-param name="node">managedAuthority</xsl:with-param>
                  <xsl:with-param name="pos" select="count(managedAuthority)"/>
                  <xsl:with-param name="delim">/</xsl:with-param>
               </xsl:call-template>
            </xsl:attribute>

         </xsl:if>
      </xsl:for-each>

      <xsl:text>
</xsl:text>

      <!-- make sure the baseURL matches the URL passed in -->
      <xsl:if test="$thebaseurl=''">
         <xsl:message>Warning: input baseurl it not set.</xsl:message>
      </xsl:if>
      <xsl:call-template name="RI3.1.5a"/>

      <!-- make sure the description contains a Registry record -->
      <!-- this will internally call validation on the Registry record -->
      <xsl:call-template name="RI3.1.5b"/>

   </xsl:template>

   <xsl:template match="oai:GetRecord" mode="tests">
      <xsl:param name="appelation">This record</xsl:param>
      <xsl:param name="chknotdeleted" select="false()"/>

      <xsl:for-each select="oai:record">

         <!-- make sure the OAI identifier matches the VOResource identifier -->
         <xsl:call-template name="RI3.1.3"/>

         <xsl:if test="$chknotdeleted">
            <!-- make sure the record is not deleted -->
            <xsl:variable name="dstat" select="oai:metadata/*[identifier]"/>
            <xsl:call-template name="reportResult">
               <xsl:with-param name="item">RI3.1.4aw</xsl:with-param>
               <xsl:with-param name="status" select="$dstat"/>
               <xsl:with-param name="type">warn</xsl:with-param>
               <xsl:with-param name="desc">
                  <xsl:value-of select="$appelation"/>
                  <xsl:text> record for this registry </xsl:text>
                  <xsl:text>should not be marked deleted.</xsl:text>
               </xsl:with-param>
            </xsl:call-template>
         </xsl:if>

         <!-- validate the VOResource record -->
         <xsl:apply-templates select="oai:metadata/ri:Resource" 
                              mode="validateResource"/>

      </xsl:for-each>

   </xsl:template>

   <!-- 
     -  make sure the baseURL matches the URL passed in
     -->
   <xsl:template name="RI3.1.5a">
      <xsl:variable name="stat">
         <xsl:copy-of select="oai:baseURL=$thebaseurl"/>
      </xsl:variable>  
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">RI3.1.5a</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="desc">
            <xsl:text>Identify/baseurl must be equal to the URL </xsl:text>
            <xsl:text>being tested (</xsl:text>
            <xsl:value-of select="$thebaseurl"/>
            <xsl:text>)</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <!-- 
     -  make sure the description contains a Registry record 
     -->
   <xsl:template name="RI3.1.5b">
      <xsl:variable name="stat1">
         <xsl:copy-of 
          select="boolean(oai:description/*[contains(@xsi:type,':Registry')])"/>
      </xsl:variable>

      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">RI3.1.5b1</xsl:with-param>
         <xsl:with-param name="status" select="$stat1"/>
         <xsl:with-param name="desc">
            <xsl:text>Identifier must include a description </xsl:text>
            <xsl:text>containing a Registry Resource record.</xsl:text>
         </xsl:with-param>
      </xsl:call-template>

      <xsl:if test="$stat1='true'">
        <xsl:variable name="stat2">
           <xsl:copy-of 
                select="boolean(oai:description/*[local-name()='Resource' and 
                                                  contains(@xsi:type,
                                                           ':Registry')])"/>
        </xsl:variable>

        <xsl:call-template name="reportResult">
           <xsl:with-param name="item">RI3.1.5b2</xsl:with-param>
           <xsl:with-param name="status" select="$stat2"/>
           <xsl:with-param name="desc">
              <xsl:text>Registry record must have an element name </xsl:text>
              <xsl:text>of 'Resource'.</xsl:text>
           </xsl:with-param>
        </xsl:call-template>

        <!-- recommend the use ri:Resource -->
        <xsl:for-each select="oai:description/*[local-name()='Resource']">
           <xsl:call-template name="riResource">
              <xsl:with-param name="code">RI3.1.5b3</xsl:with-param>
           </xsl:call-template>
        </xsl:for-each>

        <xsl:for-each 
             select="oai:description/*[contains(@xsi:type,':Registry')]">

          <xsl:variable name="stat3">
             <xsl:copy-of 
                  select="boolean(capability[contains(@xsi:type,':Harvest')])"/>
          </xsl:variable>

          <xsl:call-template name="reportResult">
             <xsl:with-param name="item">RI3.1.5b4</xsl:with-param>
             <xsl:with-param name="status" select="$stat3"/>
             <xsl:with-param name="type">warn</xsl:with-param>
             <xsl:with-param name="desc">
                <xsl:text>A Harvesting Registry should declare a </xsl:text>
                <xsl:text>Harvest capability. </xsl:text>
             </xsl:with-param>
          </xsl:call-template>
        </xsl:for-each>

        <!-- now make sure the record is a valid Registry record -->
        <xsl:apply-templates mode="validateResource"
             select="oai:description/*[contains(@xsi:type,':Registry')]" />

      </xsl:if>
   </xsl:template>

   <!--
     -  Recommend the use of the Resource element from the RegistryInterface
     -  schema
     -->
   <xsl:template name="riResource">
      <xsl:param name="code">unknown</xsl:param>
      <xsl:param name="type">warn</xsl:param>

      <xsl:variable name="stat">
         <xsl:copy-of select="boolean(self::ri:Resource)"/>         
      </xsl:variable>

      <xsl:call-template name="reportResult">
         <xsl:with-param name="item" select="$code"/>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="type" select="$type"/>
         <xsl:with-param name="desc">
            <xsl:text>Recommend using Resource from the </xsl:text>
            <xsl:text>RegistryInterface schema </xsl:text>
            <xsl:text>(http://www.ivoa.net/xml/RegistryInterface/v1.0)</xsl:text>
            <xsl:text> for full OAI schema compliance.</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <xsl:template match="ri:Resource" mode="validateResource">
      <xsl:apply-templates select="." mode="coretests"/>
      <xsl:apply-templates select="." mode="restests"/>
      <xsl:apply-templates select="capability" mode="captests"/>
   </xsl:template>

   <xsl:template match="Resource" mode="validateResource">
      <!-- may want to short circuit this one since element must be ri:Resource -->
      <xsl:apply-templates select="." mode="coretests"/>
      <xsl:apply-templates select="." mode="restests"/>
      <xsl:apply-templates select="capability" mode="captests"/>
   </xsl:template>

   <!--
     -  check the metadataFormats response 
     -->
   <xsl:template match="oai:ListMetadataFormats" mode="tests">

      <xsl:text>
</xsl:text>

      <!-- make sure ListMetadataFormats includes "ivo_vor" -->
      <xsl:variable name="hasvor">
         <xsl:copy-of 
            select="boolean(oai:metadataFormat[oai:metadataPrefix='ivo_vor'])"/>
      </xsl:variable>

      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">RI3.1.2c</xsl:with-param>
         <xsl:with-param name="status" select="$hasvor"/>
         <xsl:with-param name="desc">
            <xsl:text>ListMetadataFormats must declare support for </xsl:text>
            <xsl:text>the ivo_vor format.</xsl:text>
         </xsl:with-param>
      </xsl:call-template>

   </xsl:template>

   <!--
     -  check the ListSets response 
     -->
   <xsl:template match="oai:ListSets" mode="tests">
      <xsl:text>
</xsl:text>

      <!-- check for ivo_managed -->
      <xsl:variable name="stat1">
         <xsl:copy-of select="boolean(oai:set[oai:setSpec='ivo_managed'])"/>
      </xsl:variable>

      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">RI3.1.6a</xsl:with-param>
         <xsl:with-param name="status" select="$stat1"/>
         <xsl:with-param name="desc">
            <xsl:text>ListSets must declare support for </xsl:text>
            <xsl:text>the ivo_managed set.</xsl:text>
         </xsl:with-param>
      </xsl:call-template>

      <!-- to make sure there are no other sets starting with ivo_ -->
      <xsl:variable name="stat2">
         <xsl:copy-of select="not(oai:set[oai:setSpec!='ivo_managed' and 
                                          starts-with(oai:setSpec,'ivo_')])"/>
      </xsl:variable>

      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">RI3.1.6b</xsl:with-param>
         <xsl:with-param name="status" select="$stat2"/>
         <xsl:with-param name="desc">
            <xsl:text>A registry cannot declare new set names that </xsl:text>
            <xsl:text>begin with 'ivo_'.</xsl:text>
         </xsl:with-param>
      </xsl:call-template>

   </xsl:template>

   <xsl:template name="catvals">
      <xsl:param name="to"/>
      <xsl:param name="node"/>
      <xsl:param name="pos"/>
      <xsl:param name="delim"/>

      <xsl:choose>
         <xsl:when test="number($pos) > 0">
            <xsl:variable name="thisauth">
               <xsl:for-each select="*[local-name()=$node]">
                  <xsl:if test="position()=$pos">
                     <xsl:value-of select="normalize-space(.)"/>
                  </xsl:if>
               </xsl:for-each>
            </xsl:variable>

            <xsl:call-template name="catvals">
               <xsl:with-param name="to" 
                               select="concat($to,$thisauth,$delim)"/>
               <xsl:with-param name="node" select="$node"/>
               <xsl:with-param name="pos" select="$pos - 1"/>
               <xsl:with-param name="delim" select="$delim"/>
            </xsl:call-template>
         </xsl:when>
         <xsl:otherwise>
            <xsl:value-of select="$to"/>
         </xsl:otherwise>
      </xsl:choose>
   </xsl:template>

   <xsl:template name="collectAuthIDs">
      <xsl:variable name="nrecs" 
           select="count(//oai:metadata/ri:Resource[@status!='deleted'])"/>
      <xsl:call-template name="addAuthID">
         <xsl:with-param name="found" select="$foundAuthorityIDs"/>
         <xsl:with-param name="pos" select="number($nrecs)"/>
      </xsl:call-template>
   </xsl:template>

   <xsl:template name="addAuthID">
      <xsl:param name="found" select="'//'"/>
      <xsl:param name="pos" select="0"/>

      <xsl:choose>
         <xsl:when test="$pos > 0">

<!--
  -   This should work and would be more efficient, but I believe there is
  -   a bug in xalan.
  -
            <xsl:for-each select="//oai:metadata/ri:Resource[position()=$pos]">
  -->             
            <xsl:for-each 
                 select="//oai:metadata/ri:Resource[@status!='deleted']">
             <xsl:if test="position()=$pos">
                
               <xsl:variable name="authid">
                  <xsl:text>/</xsl:text>
                  <xsl:call-template name="getAuthorityID">
                     <xsl:with-param name="id" select="identifier"/>
                  </xsl:call-template>
                  <xsl:text>/</xsl:text>
               </xsl:variable>

               <xsl:variable name="newfound">
                  <xsl:choose>
                     <xsl:when test="contains($found,$authid)">
                        <xsl:value-of select="$found"/>
                     </xsl:when>
                     <xsl:otherwise>
                        <!-- add new authid -->
                        <xsl:value-of 
                         select="substring($found,1,string-length($found)-1)"/>
                        <xsl:value-of select="$authid"/>
                     </xsl:otherwise>
                  </xsl:choose>
               </xsl:variable>

               <!-- recurse to the next resource record -->
               <xsl:call-template name="addAuthID">
                  <xsl:with-param name="found" select="$newfound"/>
                  <xsl:with-param name="pos" select="$pos - 1"/>
               </xsl:call-template>
             </xsl:if>
            </xsl:for-each>

         </xsl:when>
         <xsl:otherwise><xsl:value-of select="$found"/></xsl:otherwise>
      </xsl:choose>
   </xsl:template>

   <xsl:template name="findAuthRecs">
      <xsl:variable name="nrecs" 
           select="count(//oai:metadata/ri:Resource[contains(@xsi:type,
                                                             ':Authority') and 
                                                    @status!='deleted'])"/>
      <xsl:call-template name="addAuthRec">
         <xsl:with-param name="found" select="$declaredAuthorityIDs"/>
         <xsl:with-param name="pos" select="number($nrecs)"/>
      </xsl:call-template>
   </xsl:template>

   <xsl:template name="addAuthRec">
      <xsl:param name="found" select="'//'"/>
      <xsl:param name="pos" select="0"/>

      <xsl:choose>
         <xsl:when test="$pos > 0">

<!--
  -   This should work and would be more efficient, but I believe there is
  -   a bug in xalan.
  -
            <xsl:for-each 
                select="//oai:metadata/ri:Resource[contains(@xsi:type,':Authority')]/self::node()[position()=$pos]">
  -->             
            <xsl:for-each 
                 select="//oai:metadata/ri:Resource[contains(@xsi:type,
                                                             ':Authority') and 
                                                    @status!='deleted']">
             <xsl:if test="position()=$pos">
                
               <xsl:variable name="authid">
                  <xsl:text>/</xsl:text>
                  <xsl:call-template name="getAuthorityID">
                     <xsl:with-param name="id" select="identifier"/>
                  </xsl:call-template>
                  <xsl:text>/</xsl:text>
               </xsl:variable>

               <xsl:variable name="newfound">
                  <xsl:choose>
                     <xsl:when test="contains($found,$authid)">
                        <xsl:value-of select="$found"/>
                     </xsl:when>
                     <xsl:otherwise>
                        <!-- add new authid -->
                        <xsl:value-of 
                         select="substring($found,1,string-length($found)-1)"/>
                        <xsl:value-of select="$authid"/>
                     </xsl:otherwise>
                  </xsl:choose>
               </xsl:variable>

               <!-- recurse to the next resource record -->
               <xsl:call-template name="addAuthRec">
                  <xsl:with-param name="found" select="$newfound"/>
                  <xsl:with-param name="pos" select="$pos - 1"/>
               </xsl:call-template>
             </xsl:if>
            </xsl:for-each>

         </xsl:when>
         <xsl:otherwise><xsl:value-of select="$found"/></xsl:otherwise>
      </xsl:choose>
   </xsl:template>

</xsl:stylesheet>
