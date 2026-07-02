<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                version="1.0">

   <xsl:template match="*[identifier]" mode="coretests">
      <xsl:if test="$rightnow!=''">
         <xsl:apply-templates select="." mode="checkDates"/>
      </xsl:if>
      <xsl:if test="$managedAuthorityIDs!='' and $managedAuthorityIDs!='//'">
         <xsl:call-template name="RI3.1.4b"/>
      </xsl:if>
      <xsl:apply-templates select="." mode="VR3.1b1"/>
      <xsl:apply-templates select="." mode="VR3.1b2"/>
      <xsl:apply-templates select="." mode="VR3.1b3"/>
      <xsl:apply-templates select="content/relationship" mode="VR3.1.3a"/>
   </xsl:template>

   <xsl:template match="*[identifier]" mode="VR3.1b1">
      <xsl:variable name="stat" select="boolean(@status)"/>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">VR3.1b1</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="type">warn</xsl:with-param>
         <xsl:with-param name="desc">
            <xsl:text>VOResource record should have a status attribute</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <xsl:template match="*[identifier]" mode="VR3.1b2">
      <xsl:variable name="stat" select="boolean(@updated)"/>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">VR3.1b2</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="type">warn</xsl:with-param>
         <xsl:with-param name="desc">
            <xsl:text>VOResource record should have an updated attribute</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <xsl:template match="*[identifier]" mode="VR3.1b3">
      <xsl:variable name="stat" select="boolean(@created)"/>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">VR3.1b3</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="type">warn</xsl:with-param>
         <xsl:with-param name="desc">
            <xsl:text>VOResource record should have a created attribute</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <xsl:template match="capability[contains(@xsi:type,':SimpleImageAccess') or
                                   @xsi:type='SimpleImageAccess']" 
                 mode="captests">

      <!-- recommend a Resource type for SIA capabilities -->
      <xsl:call-template name="SIA7.0a"/>

      <!-- insist that there is a standard ParamHTTP interface -->
      <xsl:call-template name="SIA7.0b"/>
   </xsl:template>

   <xsl:template name="SIA7.0a">
      <xsl:variable name="stat">
         <xsl:copy-of select="contains(../@xsi:type,':CatalogService') or
                              ../@xsi:type=':CatalogService'"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">SIA7.0a</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="type">rec</xsl:with-param>
         <xsl:with-param name="desc">
            <xsl:text>Recommend setting VOResource xsi:type='vs:CatalogService' on service with SimpleImageAccess capability</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <xsl:template name="SIA7.0b">
      <xsl:variable name="stat">
         <xsl:copy-of select="boolean(
                               interface[(contains(@xsi:type,':ParamHTTP') or
                               @xsi:type=':CatalogService') and @role='std'])"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">SIA7.0b</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="desc">
            <xsl:text>SimpleImageAccess capability must include interface with xsi:type='vs:ParamHTTP' and role='std'</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <xsl:template match="capability[contains(@xsi:type,':ConeSearch') or
                                   @xsi:type='ConeSearch']" mode="captests">

      <!-- recommend a Resource type for ConeSearch capabilities -->
      <xsl:call-template name="CS4.0a"/>

      <!-- insist that there is a standard ParamHTTP interface -->
      <xsl:call-template name="CS4.0b"/>
   </xsl:template>

   <xsl:template name="CS4.0a">
      <xsl:variable name="stat">
         <xsl:copy-of select="contains(../@xsi:type,':CatalogService') or
                              ../@xsi:type='CatalogService'"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">CS4.0a</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="type">rec</xsl:with-param>
         <xsl:with-param name="desc">
            <xsl:text>Recommend setting VOResource xsi:type='vs:CatalogService' on service with ConeSearch capability</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <xsl:template name="CS4.0b">
      <xsl:variable name="stat">
         <xsl:copy-of select="boolean(
                               interface[(contains(@xsi:type,':ParamHTTP') or
                               @xsi:type='ParamHTTP') and @role='std'])"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">CS4.0b</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="desc">
            <xsl:text>ConeSearch capability must include interface with xsi:type='vs:ParamHTTP' and role='std'</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <xsl:template match="*[contains(@xsi:type,':Registry') or
                          @xsi:type='Registry']" mode="restests">

      <!-- make sure we have a version 1.0 -->
      <xsl:if test="capability[contains(@xsi:type,':Harvest')]">
         <xsl:apply-templates select="." mode="RI4.3.2b"/>
      </xsl:if>
   </xsl:template>

   <xsl:template match="capability[contains(@xsi:type,':Harvest') or
                                   @xsi:type='Harvest']" mode="captests">

      <!-- recommend a Resource type for Registry capabilities -->
      <xsl:call-template name="RI4.0b"/>

      <!-- insist that there is a standard OAIHTTP interface -->
      <xsl:call-template name="RI4.0c"/>
   </xsl:template>

   <xsl:template match="capability[contains(@xsi:type,':Search') or
                                   @xsi:type='Search']" mode="captests">

      <!-- recommend a Resource type for Registry capabilities -->
      <xsl:call-template name="RI4.0b"/>

      <!-- insist that there is a standard WebService interface -->
      <xsl:call-template name="RI4.0d"/>
   </xsl:template>

   <!--
     -  make sure registry capabilities are part of a Registry resource
     -  @context  Resource element
     -->
   <xsl:template name="RI4.0b">
      <xsl:variable name="stat">
         <xsl:copy-of select="contains(../@xsi:type,':Registry') or
                              ../@xsi:type='Registry'"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">RI4.0b</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="type">rec</xsl:with-param>
         <xsl:with-param name="desc">
            <xsl:text>Recommend setting VOResource xsi:type='vg:Registry' on service with a Search or Harvest capability</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <!--
     -  make sure Harvest capability has correct Interface type
     -->
   <xsl:template name="RI4.0c">
      <xsl:variable name="stat">
         <xsl:copy-of select="boolean(
                               interface[(contains(@xsi:type,':OAIHTTP') or
                                       @xsi:type='OAIHTTP') and @role='std'])"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">RI4.0c</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="desc">
            <xsl:text>Harvest capability must include interface with xsi:type='vg:OAIHTTP' and role='std'</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <!--
     -  make sure Harvest capability has correct Interface type
     -->
   <xsl:template name="RI4.0d">
      <xsl:variable name="stat">
         <xsl:copy-of select="boolean(
                               interface[(contains(@xsi:type,':WebService') or
                                       @xsi:type='WebService') and @role='std'])"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">RI4.0c</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="desc">
            <xsl:text>Search capability must include interface with xsi:type='vr:Webservice' and role='std'</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <xsl:template match="capability[contains(@xsi:type,':SkyNode') or
                                   @xsi:type='SkyNode']" mode="captests">

      <!-- recommend a Resource type for SkyNode capabilities -->
      <xsl:call-template name="SN4.0a"/>

      <!-- insist that there is a standard ParamHTTP interface -->
      <xsl:call-template name="SN4.0b"/>
   </xsl:template>

   <xsl:template name="SN4.0a">
      <xsl:variable name="stat">
         <xsl:copy-of select="contains(../@xsi:type,':CatalogService') or
                              ../@xsi:type='CatalogService'"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">SN4.0a</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="type">rec</xsl:with-param>
         <xsl:with-param name="desc">
            <xsl:text>Recommend setting VOResource xsi:type='vs:CatalogService' on service with SkyNode capability</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <xsl:template name="SN4.0b">
      <xsl:variable name="stat">
         <xsl:copy-of select="boolean(
                               interface[(contains(@xsi:type,':WebService') or
                               @xsi:type='WebService') and @role='std'])"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">SN4.0b</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="desc">
            <xsl:text>SimpleImageAccess capability must include interface with xsi:type='vr:WebService' and role='std'</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <xsl:template match="*[contains(@xsi:type,'Service')]" mode="restests"
                 priority="0.4">

      <!-- suggest that Service have at least one capability element -->
      <xsl:call-template name="VR3.2.2a"/>
   </xsl:template>

   <!--
     -  suggest that Service have at least one capability element
     -  @context Resource element
     -->
   <xsl:template name="VR3.2.2a">
      <xsl:variable name="stat">
         <xsl:copy-of select="capability"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">VR3.2.2a</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="type">warn</xsl:with-param>
         <xsl:with-param name="desc">
            <xsl:text>Service resource should have at least one capability element</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <xsl:template match="capability" mode="captests" priority="0.3">

      <!-- suggest that capability have at least one interface element -->
      <xsl:call-template name="VR3.2.2b"/>
   </xsl:template>

   <!-- 
     -  suggest that capability have at least one interface element
     -  @context capability element
     -->
   <xsl:template name="VR3.2.2b">
      <xsl:variable name="stat">
         <xsl:copy-of select="interface"/>
      </xsl:variable>
      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">VR3.2.2a</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="type">warn</xsl:with-param>
         <xsl:with-param name="desc">
            <xsl:text>capability element should have at least one interface element</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

   <xsl:template match="*[identifier]" mode="restests" priority="0.3">

   </xsl:template>

   <xsl:template match="*[identifier]" mode="checkDates">
      <xsl:call-template name="pastdate">
         <xsl:with-param name="datetime" select="@created"/>
         <xsl:with-param name="name">created attribute</xsl:with-param>
      </xsl:call-template>

      <xsl:call-template name="pastdate">
         <xsl:with-param name="datetime" select="@updated"/>
         <xsl:with-param name="name">updated attribute</xsl:with-param>
      </xsl:call-template>

      <xsl:for-each select="curation/date">
         <xsl:call-template name="pastdate">
            <xsl:with-param name="datetime" select="."/>
            <xsl:with-param name="name">date element</xsl:with-param>
         </xsl:call-template>
      </xsl:for-each>
   </xsl:template>
   
   <!--
     -  make sure the give timestamp is in the past
     -  @param datetime  the timestampe to examine
     -  @param name      a name indicating the use of the date
     -->
   <xsl:template name="pastdate">
      <xsl:param name="datetime"/>
      <xsl:param name="name">date element</xsl:param>

      <xsl:variable name="nowday">
         <xsl:call-template name="getDate">
            <xsl:with-param name="datetime" select="$rightnow"/>
         </xsl:call-template>
      </xsl:variable>

      <xsl:variable name="thenday">
         <xsl:call-template name="getDate">
            <xsl:with-param name="datetime" select="$datetime"/>
         </xsl:call-template>
      </xsl:variable>

      <xsl:variable name="pastday">
         <xsl:call-template name="ispast">
            <xsl:with-param name="then" select="$thenday"/>
            <xsl:with-param name="now" select="$nowday"/>
            <xsl:with-param name="delim">-</xsl:with-param>
         </xsl:call-template>
      </xsl:variable>

      <xsl:variable name="pasttime">
         <xsl:choose>
            <xsl:when test="$pastday != 0">
               <xsl:copy-of select="$pastday"/>
            </xsl:when>
            <xsl:otherwise>

               <xsl:variable name="nowtime">
                  <xsl:call-template name="getTime">
                     <xsl:with-param name="datetime" select="$rightnow"/>
                  </xsl:call-template>
               </xsl:variable>

               <xsl:variable name="thentime">
                  <xsl:call-template name="getTime">
                     <xsl:with-param name="datetime" select="$datetime"/>
                  </xsl:call-template>
               </xsl:variable>

               <xsl:call-template name="ispast">
                  <xsl:with-param name="then" select="$thentime"/>
                  <xsl:with-param name="now" select="$nowtime"/>
                  <xsl:with-param name="delim">:</xsl:with-param>
               </xsl:call-template>
            </xsl:otherwise>
         </xsl:choose>
      </xsl:variable>

      <xsl:variable name="stat">
         <xsl:copy-of select="$pasttime &lt; 0"/>
      </xsl:variable>

      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">VRdate</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="desc">
            <xsl:text>The date for the </xsl:text>
            <xsl:value-of select="$name"/>
            <xsl:text> must be in the Past</xsl:text>
         </xsl:with-param>
      </xsl:call-template>

   </xsl:template>

   <!--
     -  return the date portion of a timestamp
     -->
   <xsl:template name="getDate">
      <xsl:param name="datetime"/>
      <xsl:param name="delim">T</xsl:param>

      <xsl:choose>
         <xsl:when test="contains($datetime, $delim)">
            <xsl:value-of select="substring-before($datetime, $delim)"/>
         </xsl:when>
         <xsl:otherwise><xsl:value-of select="$datetime"/></xsl:otherwise>
      </xsl:choose>
   </xsl:template>

   <!--
     -  return the time portion of a timestamp
     -->
   <xsl:template name="getTime">
      <xsl:param name="datetime"/>
      <xsl:param name="delim">T</xsl:param>

      <xsl:value-of select="substring-after($datetime, $delim)"/>
   </xsl:template>

   <!--
     -  return -1 if a purported past date/time is prior
     -  to a current date, 0 if they are the same date, or 1 if the
     -  purported past is actually after the current date
     -  @param then   the past time
     -  @param now    the current time
     -  @param delim  the delimiter to look for between date/time fields
     -->
   <xsl:template name="ispast">
      <xsl:param name="then"/>
      <xsl:param name="now"/>
      <xsl:param name="delim">-</xsl:param>

      <xsl:choose>
         <xsl:when test="normalize-space($then)=normalize-space($now)">
            <xsl:copy-of select="0"/>
         </xsl:when>
         <xsl:otherwise>

            <xsl:variable name="thenhead">
              <!-- despite the name, the function technique is generic -->
              <xsl:call-template name="getDate">
                <xsl:with-param name="datetime" select="$then"/>
                <xsl:with-param name="delim" select="$delim"/>
              </xsl:call-template>
            </xsl:variable>

            <xsl:variable name="thentail">
              <!-- despite the name, the function technique is generic -->
              <xsl:call-template name="getTime">
                <xsl:with-param name="datetime" select="$then"/>
                <xsl:with-param name="delim" select="$delim"/>
              </xsl:call-template>
            </xsl:variable>

            <xsl:variable name="nowhead">
              <!-- despite the name, the function technique is generic -->
              <xsl:call-template name="getDate">
                <xsl:with-param name="datetime" select="$now"/>
                <xsl:with-param name="delim" select="$delim"/>
              </xsl:call-template>
            </xsl:variable>

            <xsl:variable name="nowtail">
              <!-- despite the name, the function technique is generic -->
              <xsl:call-template name="getTime">
                <xsl:with-param name="datetime" select="$now"/>
                <xsl:with-param name="delim" select="$delim"/>
              </xsl:call-template>
            </xsl:variable>

            <xsl:choose>
              <xsl:when test="$thenhead &lt; $nowhead">
                 <xsl:copy-of select="-1"/>
              </xsl:when>
              <xsl:when test="$thenhead &gt; $nowhead">
                 <xsl:copy-of select="1"/>
              </xsl:when>
              <xsl:when test="$thentail = '' and $nowtail = ''">
                 <xsl:copy-of select="0"/>
              </xsl:when>
              <xsl:when test="$thentail = ''">
                 <xsl:copy-of select="-1"/>
              </xsl:when>
              <xsl:when test="$nowtail = ''">
                 <xsl:copy-of select="1"/>
              </xsl:when>
              <xsl:otherwise>
                 <!-- recurse on remaining fields -->
                 <xsl:call-template name="ispast">
                    <xsl:with-param name="then" select="$thentail"/>
                    <xsl:with-param name="now" select="$nowtail"/>
                    <xsl:with-param name="delim" select="$delim"/>
                 </xsl:call-template>
              </xsl:otherwise>
            </xsl:choose>

         </xsl:otherwise>
      </xsl:choose>

   </xsl:template>

   <!-- 
     -  make sure the Registry record is included 
     -  @context Resource element   only used when authid is not provided
     -  @optparam authid   the authority ID to assume for this resource
     -->
   <xsl:template name="RI3.1.4b">
      <xsl:param name="authid">
         <xsl:call-template name="getAuthorityID">
            <xsl:with-param name="id" select="identifier"/>
         </xsl:call-template>
      </xsl:param>

      <xsl:variable name="stat">
         <xsl:copy-of select="contains(translate($managedAuthorityIDs, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),
         translate(concat('/',$authid,'/'), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                                     'abcdefghijklmnopqrstuvwxyz'))"/>

      </xsl:variable>

      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">RI3.1.4b</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="desc">
            <xsl:text>The Registry must not serve records with </xsl:text>
            <xsl:text>authorities it does not claim in its </xsl:text>
            <xsl:text>Identify response ("managedAuthority"). </xsl:text>
         </xsl:with-param>
      </xsl:call-template>
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

   <xsl:template match="*[identifier]" mode="RI4.3.2b">
      <xsl:variable name="stat">
         <!-- make sure we have a version 1.0 -->
         <xsl:copy-of 
              select="boolean(capability[contains(@xsi:type,':Harvest')]/interface[contains(@xsi:type,':OAIHTTP') and @role='std' and (not(@version) or @version='1.0')])"/>
      </xsl:variable>

      <xsl:call-template name="reportResult">
         <xsl:with-param name="item">4.3.2b</xsl:with-param>
         <xsl:with-param name="status" select="$stat"/>
         <xsl:with-param name="desc">
            <xsl:text>A harvesting registry must support version </xsl:text>
            <xsl:text>1.0 of the OAIHTTP interface.</xsl:text>
         </xsl:with-param>
      </xsl:call-template>
   </xsl:template>

</xsl:stylesheet>
