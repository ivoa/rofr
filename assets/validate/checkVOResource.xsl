<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                exclude-result-prefixes="vr vg ri oai xsi"
                version="1.0">

   <xsl:import href="testsVOResource-v1_0.xsl"/>
   <xsl:import href="validateVocabularies.xsl"/>
   <xsl:import href="validationCommon.xsl"/>

   <xsl:output method="xml" encoding="UTF-8" indent="yes"
               omit-xml-declaration="no" />

   <!--
     -  the date and time for the execution of this validater.  This is used
     -  to ensure that stated dates are indeed in the past.  If not
     -  its an empty string, the test will not be done.
     -->
   <xsl:param name="rightnow"></xsl:param>

   <!--
     -  a slash-delimited list of authority IDs that have been declared in a
     -  registry record.  If this list is non-empty, a test will be applied
     -  to ensure that the resource's Authority ID has been registered.
     -->
   <xsl:param name="managedAuthorityIDs">//</xsl:param>

   <!--
     -  the type of query being tested.  Allowed values include:
     -  <pre>
     -
     -
     -
     -  </pre>
     -->
   <xsl:param name="role">resource</xsl:param>

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
     -  the name to give to the root element of the output results document
     -->
   <xsl:param name="resultsRootElement">VOResourceValidation</xsl:param>

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
     -  begin testing.  This template should be overridden for the appropriate
     -    output format (plain text, html, etc.).  It should provide the
     -    overall document envelope to contain the results of the various
     -    tests (via reportResult).  Within that envelope, it should apply the
     -    mode="byquery" template on "/".  This implementation returns XML
     -    encoding.
     -->
   <xsl:template match="/">
      <xsl:element name="{$resultsRootElement}">
         <xsl:attribute name="name">
            <xsl:value-of select="$queryName"/>
         </xsl:attribute>
         <xsl:attribute name="role">
            <xsl:value-of select="$role"/>
         </xsl:attribute>
         <xsl:if test="$inputs!=''">
            <xsl:attribute name="options">
               <xsl:value-of select="$inputs"/>
            </xsl:attribute>
         </xsl:if>
         <xsl:if test="*/identifier">
            <xsl:attribute name="ivo-id">
               <xsl:value-of select="normalize-space(*/identifier[1])"/>
            </xsl:attribute>
         </xsl:if>
         <xsl:if test="*/@status">
            <xsl:attribute name="status">
               <xsl:value-of select="normalize-space(*/@status)"/>
            </xsl:attribute>
         </xsl:if>

         <xsl:text>
</xsl:text>
         <xsl:apply-templates select="/*[identifier]"/>
      </xsl:element>
   </xsl:template>

   <xsl:template match="*[identifier]">
      <xsl:apply-templates select="." mode="coretests"/>
      <xsl:apply-templates select="." mode="restests"/>
      <xsl:apply-templates select="capability" mode="captests"/>
   </xsl:template>


</xsl:stylesheet>
