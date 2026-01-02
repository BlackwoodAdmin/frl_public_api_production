"""Content generation services."""
from app.database import db
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import re
import json
import os

logger = logging.getLogger(__name__)

# #region agent log
def _debug_log(location: str, message: str, data: dict, hypothesis_id: str = ""):
    """Helper function to write debug logs in NDJSON format."""
    log_path = r"d:\www\FRLPublic\.cursor\debug.log"
    try:
        log_entry = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(datetime.now().timestamp() * 1000)
        }
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception:
        pass  # Silently fail if logging fails

def _count_divs(html: str) -> dict:
    """Count opening and closing div tags, and find elementor elementor-3833."""
    if not html:
        return {"open": 0, "close": 0, "net": 0, "elementor_3833_open": 0, "elementor_3833_close": 0}
    open_divs = len(re.findall(r'<div[^>]*>', html, re.IGNORECASE))
    close_divs = len(re.findall(r'</div>', html, re.IGNORECASE))
    elementor_3833_open = len(re.findall(r'class="[^"]*elementor[^"]*elementor-3833[^"]*"', html, re.IGNORECASE))
    elementor_3833_close = 0
    # Find closing divs that might close elementor-3833 (look for pattern before </article> or </main>)
    matches = re.finditer(r'</div>\s*(?:</article>|</main>|<footer)', html, re.IGNORECASE)
    elementor_3833_close = len(list(matches))
    return {
        "open": open_divs,
        "close": close_divs,
        "net": open_divs - close_divs,
        "elementor_3833_open": elementor_3833_open,
        "elementor_3833_close": elementor_3833_close
    }
# #endregion


def get_script_version_num(script_version) -> float:
    """Convert script_version to float for comparison (handles '5.0', '5.0.x', etc.)."""
    if script_version is None:
        return 0.0
    if isinstance(script_version, (int, float)):
        return float(script_version)
    try:
        script_version_str = str(script_version)
        # Handle versions like '5.0.x' by taking first two parts
        parts = script_version_str.split('.')
        if len(parts) > 1:
            return float(parts[0] + '.' + parts[1])
        return float(script_version_str)
    except (ValueError, TypeError):
        return 0.0


def get_css_class_prefix(wp_plugin: int) -> str:
    """
    Get CSS class prefix based on wp_plugin flag.
    WordPress plugins (wp_plugin == 1) use 'seo-automation-*'
    PHP plugins (wp_plugin != 1) use 'ngodkrbsitr-*'
    """
    if wp_plugin == 1:
        return 'seo-automation'
    else:
        return 'ngodkrbsitr'


def get_header_footer(domainid: int, domain_status: Any, keyword: str = '', category: str = '', alttemplate: Optional[int] = None) -> Dict[str, Any]:
    """
    Get header and footer HTML from database templates.
    Replicates PHP Article.php lines 868-981.
    
    Returns dict with:
    - header: HTML header string
    - footer: HTML footer string
    - header_footer: Full template data dict
    - doctype: Document type string
    - style_vars: Dictionary of style variables
    """
    import html
    
    # Get default template (feedstyle_id = 1)
    default_template = db.fetch_row(
        "SELECT * FROM bwp_domain_feedstyle WHERE feedstyle_id = '1'"
    )
    
    defhead = ''
    deffoot = ''
    if default_template:
        defhead = html.unescape(default_template.get('domain_header', ''))
        defhead = defhead.replace('<old', '<')
        defhead = defhead.replace('</old', '<')
        deffoot = html.unescape(default_template.get('domain_footer', ''))
        deffoot = deffoot.replace('<old', '<')
        deffoot = deffoot.replace('</old', '<')
    
    # Check for alternative template (keyword-specific or primary)
    # PHP lines 884-921: Template selection logic
    cmstemplate = '0'
    primaryid = None
    
    if not alttemplate:
        # Get custom primary template
        primary_template = db.fetch_row(
            "SELECT feedstyle_id FROM bwp_domain_feedstyle_alt WHERE domain_id = %s AND deleted != 1 AND `primary` = 1",
            (domainid,)
        )
        if primary_template:
            primaryid = primary_template.get('feedstyle_id')
            alttemplate = primaryid
    
    # Get template data
    if alttemplate:
        # Get alternative template
        header_footer = db.fetch_row(
            "SELECT * FROM bwp_domain_feedstyle_alt WHERE feedstyle_id = %s",
            (alttemplate,)
        )
        # Fallback to domain default if alt template missing
        if not header_footer or not header_footer.get('domain_header'):
            header_footer = db.fetch_row(
                "SELECT * FROM bwp_domain_feedstyle WHERE domain_id = %s",
                (domainid,)
            )
    else:
        # Get domain default template
        header_footer = db.fetch_row(
            "SELECT * FROM bwp_domain_feedstyle WHERE domain_id = %s",
            (domainid,)
        )
    
    # Fallback to system default (feedstyle_id = 2) if domain template missing
    if not header_footer or not header_footer.get('domain_header'):
        header_footer = db.fetch_row(
            "SELECT * FROM bwp_domain_feedstyle WHERE feedstyle_id = '2'"
        )
    
    # Decode header and footer
    header = html.unescape(header_footer.get('domain_header', '')) if header_footer else ''
    footer = html.unescape(header_footer.get('domain_footer', '')) if header_footer else ''
    
    # #region agent log
    header_div_counts = _count_divs(header)
    footer_div_counts = _count_divs(footer)
    _debug_log("content.py:get_header_footer", "After header/footer decoded", {
        "header_length": len(header),
        "footer_length": len(footer),
        "header_div_counts": header_div_counts,
        "footer_div_counts": footer_div_counts
    }, "C")
    # #endregion
    
    # Add style tag if domain_smalltextcolor is set (PHP line 971-975)
    if header_footer and header_footer.get('domain_smalltextcolor'):
        font_color = header_footer['domain_smalltextcolor']
        header += f'\n<style>.ngodkrbsitr-main-table{{color:{font_color};}}</style>\n'
    
    # Use default if domain status is 0 or 1 or header is empty (PHP line 977-981)
    if domain_status in [0, 1] or not header:
        header = defhead
        footer = deffoot
    
    # Get doctype
    doctype = html.unescape(header_footer.get('domain_doctype', '')) if header_footer else ''
    
    # Set default style values (PHP lines 984-1012)
    style_vars = {}
    if header_footer:
        style_vars['blogtitlecolor'] = header_footer.get('blogtitlecolor') or 'black'
        style_vars['blogdatecolor'] = header_footer.get('blogdatecolor') or 'black'
        style_vars['blogcontentcolor'] = header_footer.get('blogcontentcolor') or 'black'
        style_vars['domain_fontcolor'] = header_footer.get('domain_fontcolor') or 'black'
        style_vars['domain_smalltextcolor'] = header_footer.get('domain_smalltextcolor') or 'black'
        style_vars['domain_headercolor'] = header_footer.get('domain_headercolor') or 'black'
        style_vars['domain_linkcolor'] = header_footer.get('domain_linkcolor') or 'blue'
        style_vars['domain_linkhover'] = header_footer.get('domain_linkhover') or 'black'
        style_vars['domain_linkvisited'] = header_footer.get('domain_linkvisited') or 'blue'
        style_vars['domain_notescolor'] = header_footer.get('domain_notescolor') or 'black'
        style_vars['domain_linksmallcolor'] = header_footer.get('domain_linksmallcolor') or 'blue'
        style_vars['domain_linksmallhover'] = header_footer.get('domain_linksmallhover') or 'black'
        style_vars['domain_linksmallvisited'] = header_footer.get('domain_linksmallvisited') or 'blue'
        
        # Build style strings (PHP lines 997-1009)
        style_vars['blogtitle'] = f"color:{style_vars['blogtitlecolor']};font-family:{header_footer.get('blogtitlefont', '')};text-decoration:none;font-size:{header_footer.get('blogtitlesize', '')}pt;font-weight:{header_footer.get('blogtitlewight', '')}"
        style_vars['blogdate'] = f"color:{style_vars['blogdatecolor']};font-family:{header_footer.get('blogdatefont', '')};text-decoration:none;font-size:{header_footer.get('blogdatesize', '')}pt;font-weight:{header_footer.get('blogdateweight', '')}"
        style_vars['blogcontent'] = f"color:{style_vars['blogcontentcolor']};font-family:{header_footer.get('blogcontentfont', '')};text-decoration:none;font-size:{header_footer.get('blogcontentsize', '')}pt;font-weight:{header_footer.get('blogcontentweight', '')}"
        style_vars['main_page_style'] = f"color:{style_vars['domain_fontcolor']}; font-family:{header_footer.get('domain_fontface', '')}; font-size:{header_footer.get('domain_fontsize', '')}pt; font-weight:{header_footer.get('domain_fontweight', '')};"
        style_vars['main_page_style_small'] = f"color:{style_vars['domain_smalltextcolor']}; font-family:{header_footer.get('domain_smalltextfont', '')}; font-size:{header_footer.get('domain_smalltextsize', '')}pt; font-weight:{header_footer.get('domain_smalltextweight', '')};"
        style_vars['main_page_style_header'] = f"color:{style_vars['domain_headercolor']}; font-family:{header_footer.get('domain_headerfont', '')}; font-size:{header_footer.get('domain_headersize', '')}pt; font-weight:{header_footer.get('domain_headerweight', '')};"
        style_vars['main_page_links'] = f" color:{style_vars['domain_linkcolor']}; font-family:{header_footer.get('domain_linkfont', '')}; font-size:{header_footer.get('domain_linkfontsize', '')}pt; font-weight:{header_footer.get('domain_linkweight', '')}; text-decoration:{header_footer.get('domain_linkdecoration', '')};\""
        style_vars['main_page_links'] += f" onMouseOver=\"this.style.color='{style_vars['domain_linkhover']}';\" onMouseOut=\"this.style.color='{style_vars['domain_linkvisited']}';"
        style_vars['misc_notes'] = f"color:{style_vars['domain_notescolor']}; font-family:{header_footer.get('domain_notesfont', '')}; font-size:{header_footer.get('domain_notessize', '')}pt; font-weight:{header_footer.get('domain_notesweight', '')};"
        style_vars['main_page_links_small'] = f' color:{style_vars["domain_linksmallcolor"]}; font-family:{header_footer.get("domain_linksmallfont", "")}; font-size:{header_footer.get("domain_linksmallfontsize", "")}pt; font-weight:{header_footer.get("domain_linksmallweight", "")}; text-decoration:{header_footer.get("domain_linksmalldecoration", "")};"'
        style_vars['main_page_links_small'] += f" onMouseOver=\"this.style.color='{style_vars['domain_linksmallhover']}';\" onMouseOut=\"this.style.color='{style_vars['domain_linksmallvisited']}';"
        style_vars['wr_style_small'] = f'color:{style_vars["domain_fontcolor"]}; font-family:{header_footer.get("domain_fontface", "")}; font-size:{header_footer.get("domain_fontsize", "")}pt; font-weight:bold;'
        style_vars['wr_style_large'] = f'color:{style_vars["domain_fontcolor"]}; font-family:{header_footer.get("domain_headerfont", "")}; font-size:{header_footer.get("domain_headersize", "")}pt; font-weight:bold;'
    
    return {
        'header': header,
        'footer': footer,
        'header_footer': header_footer or {},
        'doctype': doctype,
        'style_vars': style_vars
    }


def build_metaheader(
    domainid: int,
    domain_data: Dict[str, Any],
    domain_settings: Dict[str, Any],
    action: str,
    keyword: str = '',
    pageid: int = 0,
    category: str = '',
    city: str = '',
    state: str = '',
    st: str = '',
    bubble: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build meta header HTML (title, description, keywords, og tags).
    Replicates PHP Article.php lines 1016-1289.
    """
    import html
    import re
    
    # Get domain category
    domain_category_sql = """
        SELECT dom.*, cat.category 
        FROM bwp_domains dom 
        INNER JOIN bwp_domain_category cat ON domain_category = cat.id 
        WHERE dom.id = %s
    """
    metadomain = db.fetch_row(domain_category_sql, (domainid,))
    
    if not metadomain:
        metadomain = domain_data
    
    # Get keywords
    metakeywords = get_domain_keywords(domainid)
    if not metakeywords:
        metakeywords = [domain_data.get('domain_name', '')]
    
    # Find matching keyword
    import random
    metakey = None
    if keyword:
        try:
            metakey = metakeywords.index(keyword.lower())
        except ValueError:
            metakey = None
    
    if metakey is None:
        metakey = random.randint(0, len(metakeywords) - 1) if metakeywords else 0
    
    metaKeywords = metakeywords[metakey] if metakeywords else keyword
    
    # Build meta title and description based on action
    metaTitle = ''
    metaDesc = ''
    
    if action == '1':
        # Website Reference
        if bubble:
            if bubble.get('metatitle') and bubble['metatitle'].strip():
                metaTitle = clean_title(seo_filter_text_custom(bubble['metatitle']))
                metaKeywords = seo_filter_text_custom(bubble.get('restitle', ''))
            else:
                metaTitle = clean_title(seo_filter_text_custom(bubble.get('restitle', '')))
                metaKeywords = seo_filter_text_custom(bubble.get('restitle', ''))
            
            if bubble.get('metadescription') and bubble['metadescription'].strip():
                metaDesc = re.sub(r'\r|\n', ' ', seo_filter_text_custom(bubble['metadescription']))
            else:
                # Extract first 20 words from resfulltext
                resfulltext = html.unescape(seo_filter_text_custom(bubble.get('resfulltext', '')))
                resfulltext = re.sub(r'<[^>]+>', '', resfulltext)  # strip tags
                words = resfulltext.split()[:20]
                content = ' '.join(words)
                metaDesc = content.replace('Table of Contents', '').strip() + '... ' + metaTitle
            
            # Add phone to title if configured
            if len(metadomain.get('wr_phone', '')) > 9 and domain_settings.get('phoneintitle') == 1:
                metaTitle = metadomain['wr_phone'] + ' - ' + metaTitle
        else:
            metaTitle = keyword or metaKeywords
            metaDesc = metadomain.get('desc2', '') or metaTitle
    elif action == '2':
        # Business Collective
        if bubble:
            metaTitle = seo_filter_text_custom(bubble.get('restitle', '')) + ' - Resources'
            metaDesc = seo_filter_text_custom(bubble.get('restitle', '')) + ' - Resources'
            metaKeywords = seo_filter_text_custom(bubble.get('restitle', ''))
            
            if len(metadomain.get('wr_phone', '')) > 9 and domain_settings.get('phoneintitle') == 1:
                metaTitle = metadomain['wr_phone'] + ' - ' + metaTitle
        else:
            metaTitle = keyword or metaKeywords
            metaDesc = metadomain.get('desc2', '') or metaTitle
    
    # Add city/state to meta if provided
    if city:
        metaDesc = (city + ': ' + metaDesc).strip()
        metaTitle = clean_title(city + ' - ' + metaTitle) + ' - ' + domain_data.get('domain_name', '')
        metaKeywords = (metaKeywords + ' ' + city).strip()
    elif state:
        metaDesc = (state + ' - ' + st + ': ' + metaDesc).strip()
        metaTitle = clean_title((state + ' - ' + metaTitle).strip()) + ' - ' + domain_data.get('domain_name', '')
        metaKeywords = (metaKeywords + ' ' + state + ', ' + metaKeywords + ' ' + st).strip()
    
    # Build metaheader HTML (PHP lines 1269-1288)
    metaheader = ''
    metaheader += f'<title>{seo_filter_text_custom(metaTitle)}</title>\n'
    metaheader += f'<meta name="description" content="{seo_filter_text_custom(metaDesc)}"/>\n'
    metaheader += f'<meta name="keywords" content="{seo_filter_text_custom(metaKeywords)}"/>\n'
    metaheader += f'<meta property="og:title" content="{seo_filter_text_custom(metaTitle)}">\n'
    metaheader += f'<meta property="og:description" content="{seo_filter_text_custom(metaDesc)}"/>\n'
    
    if domain_data.get('domain_country') == 'US':
        metaheader += '<meta property="og:locale" content="en_US" />\n'
    
    # Add Umami analytics if configured
    if domain_settings.get('umamiid') and domain_settings['umamiid'].strip():
        metaheader += f'<script async src="https://analytics.umami.is/script.js" data-website-id="{domain_settings["umamiid"]}"></script>\n'
    
    return metaheader


def wrap_content_with_header_footer(
    content: str,
    header: str,
    footer: str,
    metaheader: str,
    canonical_url: str = '',
    websitereferencesimple: bool = False,
    wp_plugin: int = 0
) -> str:
    """
    Wrap content with header and footer HTML.
    Replicates PHP websitereference.php lines 263-294 (header) and 1761-1785 (footer).
    
    Args:
        content: Main content HTML
        header: Header HTML from template
        footer: Footer HTML from template
        metaheader: Meta tags HTML
        canonical_url: Canonical link URL
        websitereferencesimple: If True, skip header/footer (for simple mode)
        wp_plugin: If 1, skip header/footer (WordPress handles it)
    """
    # #region agent log
    _debug_log("content.py:wrap_content_with_header_footer", "Function entry", {
        "content_length": len(content) if content else 0,
        "header_length": len(header) if header else 0,
        "footer_length": len(footer) if footer else 0,
        "wp_plugin": wp_plugin,
        "websitereferencesimple": websitereferencesimple
    }, "B")
    content_div_counts = _count_divs(content) if content else {}
    header_div_counts = _count_divs(header) if header else {}
    _debug_log("content.py:wrap_content_with_header_footer", "Input div counts", {
        "content_div_counts": content_div_counts,
        "header_div_counts": header_div_counts
    }, "B")
    # #endregion
    
    # WordPress plugin doesn't use header/footer (WordPress handles it)
    if wp_plugin == 1:
        return content
    
    # Simple mode doesn't use header/footer
    if websitereferencesimple:
        return content
    
    full_page = ''
    
    # Build header section (PHP lines 263-294)
    ishead = '</head>' in header.lower() if header else False
    
    # Include feed.css.php and feed.js.php (PHP lines 272-273, 288-289)
    feed_css_js = '''<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@3.3.7/dist/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">
<style type="text/css">
.seo-automation-main-table .row .col-md-6 {
/*	display:list-item; */
}
.moinfomation { margin-left:60px !important;}

.vid-container { float:none!important; margin:0px auto!important; text-align:center!important; }

.xr007div {
    background-color: #fff !important;
    color:#000 !important;
}
.xr007div ul {
	-webkit-font-smoothing:antialiased;
	text-shadow:0 1px 0 #FFF;
    list-style: none;
    margin: 0;
    padding: 0;
    width: 100%;
    background-color: inherit !important;
}
.xr007div li.cfl707 {
     margin: 0;
    padding: 15px;
    position: relative;
  	 width:100%;
  	 background-color: inherit !important;
}
.xr007div li.cfl707 {
     display: block;
    text-decoration: none;
    -webkit-transition: all .35s ease;
       -moz-transition: all .35s ease;
        -ms-transition: all .35s ease;
         -o-transition: all .35s ease;
            transition: all .35s ease;
}
.xr007div li.cfl707 ul {
    left: 0;
    opacity: 0;
    position: absolute;
    top: 35px;
    visibility: hidden;
    z-index: 1;
    -webkit-transition: all .35s ease;
       -moz-transition: all .35s ease;
        -ms-transition: all .35s ease;
         -o-transition: all .35s ease;
            transition: all .35s ease;
	background-color: inherit !important;
}
.xr007div li.cfl707:hover ul {
    opacity: 1;
    top: 25px;
    visibility: visible;
    background-color: inherit !important;
}
.xr007div li.cfl707 ul li.cfl707 {
    float: none;
    width: 100%;
    background-color: inherit !important;
}

/* Clearfix */

/* Clearfix */

.cf707:after, .cf707:before {
    content:"";
    display:table;
}
.cf707:after {
    clear:both;
}
.cf707 {
    zoom:1;
}
.ngodkrbsitr-sidebar {   max-width: 29% !important; width: 300px !important; margin: 0 !important; border: 1px solid !important;; padding: 15px 2% !important;;}
.wr-fulltext { text-align:left!important; padding0px !important; /*max-width:65% !important; */ margin:0!important; float: left !important; }
.wr-fulltext img {height: auto !important;min-width:100%;}
@media (min-width: 992px){.wr-fulltext img {min-width:0;}}
.wr-fulltext-blog { text-align:left!important; padding0px !important; max-width:65% !important; margin:0!important; float: right !important; }
.ngodkrbsitr-sidebar input, .ngodkrbsitr-sidebar textarea { max-width:85% !important;	 }
.google-map a { font-size:12px !important;	 }
.fb-comments { width:100% !important;	 	 }			
.fb-comments, .fb-comments iframe[style] { max-width: 100% !important; }		
.mdubgwi-fb-comments { font-weight:bold!important; font-size:18px !important;line-height: 20px !important;}
.google-map { padding-top:30px !important; width:290px !important; overflow:hidden!important;		 }			
.google-map iframe { position:static!important;}
.ngodkrbsitr-spacer { clear:both!important; height:5px !important; display:block!important;width:100%!important; }
.ngodkrbsitr-social { margin: 0 3px !important; padding: 0px !important; float:left!important;	 }
.ngodkrbsitr-social-container {float:left!important; margin: 0px 0px 10px !important;}
.related-art-social img { margin: 0 1px !important; padding: 0px !important; max-width: 16px !important;height:auto !important; text-align:left!important; display:inline !important;}
.related-art-social {text-align:center  !important; margin:0 auto  !important;}
.ngodkrbsitr-sidebar li { padding:5px 0!important; margin:0!important; text-align:center!important; }
.ngodkrbsitr-main-table-blog .ngodkrbsitr-sidebar li { font-weight:bold !important; }
.ngodkrbsitr-main-table-blog li { margin:0px !important;list-style:none !important;	 font-size:16px !important; font-weight:normal !important; }
.ngodkrbsitr-main-table-blog li a {background:transparent !important;margin:0px !important; font-size:12px !important; font-weight:normal!important; text-decoration:none !important; color: inherit!important; }
.ngodkrbsitr-main-table-notlive, .ngodkrbsitr-main-table, .ngodkrbsitr-main-table-blog {z-index: 99999999 !important;  margin:0 auto 85px !important; width:90%; max-width:1250px; border:0!important; padding:5px 2%!important; }
.align-left { float:left!important; border:0!important; margin-right:1% !important; margin-bottom:10px !important; }
.align-right { float:right!important; margin-left:1% !important; text-align:right!important; margin-bottom:10px !important; }
img.align-left { max-width:100%!important; }
.vid-container { float:none !important; width:100% !important; margin:0 auto 20px !important; text-align:center !important;}
.vid-container iframe { max-width:100% !important; border:none; !important;}
.snapshot-container { vertical-align:middle!important; text-align:center!important; width:120px !important;   margin: 5px 0 35px 10px !important; padding: 0px !important; float:right!important; overflow:hidden!important; }
.snapshot-container img { float:right!important; border:0px !important; margin:0!important; }
.ngodkrbsitr-tag-container { text-align:left!important; font-size:13px;}
.ngodkrbsitr-top-container { min-height:220px  }
.ngodkrbsitr-container { text-align:justify!important; vertical-align:top!important; padding:0px !important; min-height:130px !important;	!important; background: inherit !important; }
.ngodkrbsitr-containerwr { text-align:justify!important; vertical-align:top!important; padding:0 15px 5px !important; }
.h1 a {clear:none !important;display:block !important;border:none !important;text-decoration:none !important; color: inherit!important; }
.h1 {display:block !important;clear:none !important;border:none !important;display:block !important;background:transparent !important;display:block!important; text-align:left !important; padding:0px !important; font-size: 30px !important; margin:10px 0px 10px !important; font-weight:bold!important; }
.h2 a {display:block !important;clear:none !important;border:none !important;font-size: 22px !important; text-decoration:none!important; color:inherit!important; }
.h2 {display:block !important;clear:none !important;border:none !important;display:block !important; background:transparent !important;text-align:left !important; font-size: 14px !important; margin:5px 0 5px !important; padding:0px !important; font-weight:bold !important; }
.h3{display:block !important;clear:none !important;border:none !important;font-size:13px !important;}
.h4{display:block !important;clear:none !important;border:none !important;font-size:12px !important;}
ul.mdubgwi-footer-nav {padding: 0px !important;overflow:visible !important}

#mdubgwi-hidden-button {  height:0px !important; width:0px !important;	 }

.mdubgwi-button { display:block!important; visibility:visible!important; height:20px !important; width:150px !important; margin:0px !important; padding:0 !important; }

.mdubgwi-footer-section {z-index: 99999999 !important; overflow:visible !important; display:block !important; position: relative !important; bottom: 0px !important; width: 250px !important; margin:0 auto !important; }
.mdubgwi-footer-section.plain ul {list-style: none !important; margin:0 auto !important; text-align:center!important;}

.mdubgwi-footer-nav li ul li {border:none !important;overflow-x: visible !important;overflow-y: visible !important;text-align:center !important; margin:0px !important;position: relative!important; color: #00397c !important; padding:0px !important; display:block !important; }
.mdubgwi-footer-section.num-plain li {list-style: none !important; display:inline !important;}
.num-lite li ul  { position: absolute !important; bottom: 45px !important; }
.mdubgwi-footer-nav li ul  {position: absolute !important;left:43% !important; min-width:100px !important; -ms-filter: "progid:DXImageTransform.Microsoft.Alpha(Opacity=0.8)" !important; -moz-opacity: 0.8 !important; -khtml-opacity: 0.8 ! important!important;  opacity: 0.8 !important; font-size: 13px !important;  float:none !important; margin:0px !important;  list-style: none !important; line-height: 18px !important; background: #fff !important; display: none !important; visibility: hidden !important; z-index: -1 !important; }
.mdubgwi-sub-nav {width:350px;}
.mdubgwi-footer-nav li ul li ul {min-width:200px !important; -ms-filter: "progid:DXImageTransform.Microsoft.Alpha(Opacity=0.8)" !important; -moz-opacity: 0.8 !important; -khtml-opacity: 0.8 ! important!important;  opacity: 0.8 !important; font-size: 13px !important;  float:none !important; margin:0px !important;  list-style: none !important; line-height: 18px !important; background: #fff !important; display: none !important; visibility: hidden !important; z-index: -1 !important; }
.mdubgwi-footer-nav:hover li ul {overflow:visible !important; -ms-filter: "progid:DXImageTransform.Microsoft.Alpha(Opacity=0.8)" !important; -moz-opacity: 0.8 !important; -khtml-opacity: 0.8 ! important!important;  opacity: 0.8 !important; list-style:none !important; display: block !important; visibility: visible !important; z-index: 999999 !important; }
.mdubgwi-footer-nav:hover li ul li ul {overflow:visible !important; min-width:200px !important; -ms-filter: "progid:DXImageTransform.Microsoft.Alpha(Opacity=0.8)" !important; -moz-opacity: 0.8 !important; -khtml-opacity: 0.8 ! important!important;  opacity: 0.8 !important; font-size: 13px !important;  float:none !important; margin:0px !important;  list-style: none !important; line-height: 18px !important; background: #fff !important; display: none !important; visibility: hidden !important; z-index: -1 !important; }
.mdubgwi-footer-nav li a {background:transparent !important; padding:5px 5px !important;text-align:center !important;  color: #00397c; text-decoration:none !important; border:0 !important; line-height: 18px !important; font-size:13px !important; color: #00397c !important; }
.mdubgwi-footer-nav li {list-style:none !important; background:transparent !important; padding:5px 5px !important;text-align:center !important;  color: #00397c; text-decoration:none !important; border:0 !important; line-height: 18px !important; font-size:13px !important; }
.mdubgwi-footer-nav li ul li a {display:inline !important;border:none !important;background:transparent !important; margin:0px !important; text-align:center !important;  color: #00397c !important; text-decoration:none !important; border:0 !important; line-height: 18px !important; font-size:13px !important; }
.mdubgwi-footer-nav li ul { padding:5px 5px 10px 5px !important; margin:0 !important; }
.mdubgwi-footer-nav li ul:hover {overflow:visible !important; -ms-filter: "progid:DXImageTransform.Microsoft.Alpha(Opacity=1.0)" !important; -moz-opacity: 1.0 !important; -khtml-opacity: 1.0 ! important!important;  opacity: 1.0 !important;      -webkit-transition: opacity 1s ease!important;     -moz-transition: opacity 1s ease!important;     -o-transition: opacity 1s ease!important;     -ms-transition: opacity 1s ease!important;        transition: opacity 1s ease!important;  list-style:none !important; display: block !important; visibility: visible !important; z-index: 999999 !important; }
.mdubgwi-footer-nav li ul:hover li ul {overflow:visible !important;  min-width:200px !important; -ms-filter: "progid:DXImageTransform.Microsoft.Alpha(Opacity=0.8)" !important; -moz-opacity: 0.8 !important; -khtml-opacity: 0.8 ! important!important;  opacity: 0.8 !important; font-size: 13px !important;  float:none !important; margin:0px !important;  list-style: none !important; line-height: 18px !important; background: #fff !important; display: none !important; visibility: hidden !important; z-index: -1 !important; }
.mdubgwi-footer-nav li ul li {border:none !important;background:transparent !important;overflow-x: visible !important;overflow-y: visible !important; text-align: center !important;margin:0px !important; position: relative!important; list-style:none !important; }
.mdubgwi-footer-nav li ul li:hover ul{overflow:visible !important;  display: block !important; visibility: visible !important; z-index: 999999 !important; -webkit-transition: all 1s ease-out!important; -moz-transition: all 1s ease-out!important; -o-transition: all 1s ease-out!important; -ms-transition: all 1s ease-out!important; transition: all 1s ease-out!important;}
.mdubgwi-footer-nav li ul li ul {border:none !important;bottom:0px !important;padding: 5px 5px 15px 5px !important;  -webkit-transition: all 1s ease-out!important; -moz-transition: all 1s ease-out!important; -o-transition: all 1s ease-out!important; -ms-transition: all 1s ease-out!important; transition: all 1s ease-out!important;position: absolute !important; }
.mdubgwi-footer-nav li ul li ul li {border:none !important; background:transparent !important; overflow-x: visible !important;overflow-y: visible !important;left:0 !important; text-align: center !important;margin:0px !important; list-style:none !important; padding:0px 5px !important; }
.bwp_citation_conatainer div {padding:0px !important;margin:0px !important;}
.bwp_citation_conatainer {text-align:left !important; float:left !important; width:44% !important; margin:15px 10px 45px 0 !important;}
.bwp_citation_conatainer .citation_map_container {padding:0px !important;float:left !important;margin:0 8px 0 0 !important}
.bwp_citation_conatainer .citation_map_container img {padding:0px !important;float:left!important; border:0px !important; margin:0 0 0 7px !important; }
.citation_map_container {float:left !important; margin:0 0 0 8px !important;}
.bwp_citation_conatainer .ngodkrbsitr-social { margin: 0 3px !important; padding: 0px !important; float:left!important;	 }
.bwp_citation_conatainer .ngodkrbsitr-social-container {float:left!important; margin: 0px 0px 10px !important;}
.bwp_citation_conatainer .related-art-social img { margin: 0 1px !important; padding: 0px !important; max-width: 16px !important;height:auto !important; text-align:left!important; display:inline !important;}
.bwp_citation_conatainer .related-art-social {clear:left !important;float:left !important;text-align:center  !important; margin:0 auto  !important;}
.bwp_citation_conatainer br {font-size:3px !important;line-height:3px !important;}
.bwp_citation_conatainer p {float:left !important;}
.mobileclear-343 {margin:0 !important; padding:0px !important;height:10px !important;}
.bwp_citation_conatainer a {float:left !important;}
@media (min-width: 768px) and (max-width: 979px) { 
.ngodkrbsitr-container { text-align:left!important; }	 
.align-left, .align-right { float:left!important; margin- right:1% !important; text-align: left !important; } 
.vid-container iframe { max-height:320px !important; }
.bwp_citation_conatainer {margin:15px 10px 10px 10px !important; width:50% !important;}
}
@media (max-width: 767px) { 
.mobileclear-343 {clear:both;}
.bwp_citation_conatainer .related-art-social {float:left  !important;}
.bwp_citation_conatainer {padding: 0px 10% !important; text-align:left !important; float:none !important; width:80% !important; margin:15px auto !important;}
.bwp_citation_conatainer .citation_map_container {margin:0 !important}
.bwp_citation_conatainer .citation_map_container img { border:0px !important; margin:0 10px 0 10px !important; }
.citation_map_container { margin:0 0 0 10px !important;}
.align-left, .align-right { float:none !important; margin:25px auto !important; text-align: left !important; display:block !important; } 
.vid-container iframe { max-height:320px !important; }
.ngodkrbsitr-main-table .h1, .ngodkrbsitr-main-table .h2, .ngodkrbsitr-main-table .h3, .ngodkrbsitr-main-table .h4, .ngodkrbsitr-main-table .h5, .ngodkrbsitr-main-table .h6, .ngodkrbsitr-main-table  h1, .ngodkrbsitr-main-table  h2, .ngodkrbsitr-main-table  h3, .ngodkrbsitr-main-table  h4, .ngodkrbsitr-main-table  h5, .ngodkrbsitr-main-table  h6 {
    margin-top: 0.ngodkrbsitr-main-table .5rem;
    margin-bottom: 0.5rem;
}
.ngodkrbsitr-container { text-align:left !important; }	 
.align-left, .align-right { float:none !important; display:block !important; margin:0 auto !important; text-align:  !important; } img.align-left { max-width:100%!important; } 
.ngodkrbsitr-social-container { float: none!important;	 display:block!important; margin:0 auto!important; }	 
.mdubgwi-sub-nav li ul  {display:none !important; visibility:hidden !important;}
.mdubgwi-sub-nav li:hover ul {overflow:visible !important; display:block !important; visibility:visible !important;}
.container.justify-content-center {max-width:100%;margin-bottom:15px;}
</style>
<script type="text/javascript" src="https://apis.google.com/js/plusone.js"></script><script src="https://cdn.jsdelivr.net/npm/bootstrap@3.3.7/dist/js/bootstrap.min.js" integrity="sha384-Tc5IQib027qvyjSMfHjOMaLkfuWVxZxUPnCJA7l2mCWNIpG9mGCD8wGNIcPD7Txa" crossorigin="anonymous"></script>
'''
    
    if not ishead:
        # Header doesn't contain </head> - output full HTML structure
        full_page += '<html>\n'
        full_page += '<head>\n'
        full_page += feed_css_js
        full_page += metaheader
        if canonical_url:
            full_page += f'<link href="{canonical_url}" rel="canonical" />\n'
        full_page += '</head>\n'
        full_page += '<body>\n'
        # Note: feed.bodytop.php would be included here in PHP
        full_page += header if header else ''
    else:
        # Header contains </head> - split and insert metaheader
        header_lower = header.lower()
        head_pos = header_lower.find('</head>')
        if head_pos >= 0:
            full_page += header[:head_pos]  # Everything before </head>
            full_page += metaheader
            full_page += feed_css_js
            if canonical_url:
                full_page += f'<link href="{canonical_url}" rel="canonical" />\n'
            full_page += header[head_pos:]  # </head> and everything after
        else:
            full_page += header
        # Note: feed.bodytop.php would be included here in PHP
    
    # #region agent log
    div_counts_after_header = _count_divs(full_page)
    _debug_log("content.py:wrap_content_with_header_footer", "After header added", {
        "full_page_length": len(full_page),
        "div_counts": div_counts_after_header
    }, "B")
    # #endregion
    
    # Add main content
    full_page += content
    
    # #region agent log
    div_counts_after_content = _count_divs(full_page)
    _debug_log("content.py:wrap_content_with_header_footer", "After content added", {
        "full_page_length": len(full_page),
        "div_counts": div_counts_after_content
    }, "B")
    # #endregion
    
    # Build footer section (PHP lines 1761-1785)
    isfoothtml = '</html>' in footer.lower() if footer else False
    isfootbody = '</body>' in footer.lower() if footer else False
    
    # Check if footer should be inserted before closing elementor elementor-3833 div
    # The footer from the database contains the contact info section (elementor-element-d448dc3)
    # which should be INSIDE the elementor elementor-3833 div
    if footer:
        import re
        
        # Check if the footer contains elementor-element-d448dc3 (contact info section)
        has_contact_section = 'elementor-element-d448dc3' in footer.lower()
        
        if has_contact_section:
            # The footer contains the contact info section that should be inside elementor elementor-3833
            # Find the closing </div> for elementor elementor-3833
            # This div closes after the main content but before the WordPress footer
            # Look for </div> followed by </article> or </main> or <footer class="wd-footer"
            # We need to insert the footer BEFORE this closing div
            
            # First, try to find the closing </div> for elementor elementor-3833 by looking backwards from </article>
            # Pattern 1: Find </div> that closes elementor-3833, followed by </article> or </main> or <footer
            closing_div_pattern = r'(</div>\s*(?:</article>|</main>|<footer\s+class="wd-footer"))'
            matches = list(re.finditer(closing_div_pattern, full_page, re.IGNORECASE | re.DOTALL))
            
            # Pattern 2: Find </div> before </article> (more flexible whitespace)
            if not matches:
                article_pattern = r'(</div>\s*</article>)'
                matches = list(re.finditer(article_pattern, full_page, re.IGNORECASE | re.DOTALL))
            
            # Pattern 3: Find </div> before </main>
            if not matches:
                main_pattern = r'(</div>\s*</main>)'
                matches = list(re.finditer(main_pattern, full_page, re.IGNORECASE | re.DOTALL))
            
            # Pattern 4: Find </div> before <footer class="wd-footer"
            if not matches:
                footer_pattern = r'(</div>\s*<footer\s+class="wd-footer")'
                matches = list(re.finditer(footer_pattern, full_page, re.IGNORECASE | re.DOTALL))
            
            if matches:
                # Insert footer before the last match (which should be the closing div for elementor elementor-3833)
                last_match = matches[-1]
                insert_pos = last_match.start()
                # #region agent log
                _debug_log("content.py:wrap_content_with_header_footer", "Before footer insertion", {
                    "insert_pos": insert_pos,
                    "matches_count": len(matches),
                    "context_before": full_page[max(0, insert_pos-100):insert_pos],
                    "context_after": full_page[insert_pos:min(len(full_page), insert_pos+100)]
                }, "B")
                # #endregion
                full_page = full_page[:insert_pos] + footer + full_page[insert_pos:]
            else:
                # Fallback: append footer after content
                # #region agent log
                _debug_log("content.py:wrap_content_with_header_footer", "Appending footer (no match found)", {}, "B")
                # #endregion
                full_page += footer
        else:
            # Footer doesn't contain contact section, append normally
            # #region agent log
            _debug_log("content.py:wrap_content_with_header_footer", "Appending footer (no contact section)", {}, "B")
            # #endregion
            full_page += footer
    
    # #region agent log
    div_counts_after_footer = _count_divs(full_page)
    _debug_log("content.py:wrap_content_with_header_footer", "After footer added", {
        "full_page_length": len(full_page),
        "div_counts": div_counts_after_footer
    }, "B")
    # #endregion
    
    if not isfoothtml and not isfootbody:
        # Footer doesn't contain </html> or </body>
        # Note: webtabs.inc.php and feed.footer.php would be included here in PHP
        full_page += '</body>\n'
        full_page += '</html>\n'
    elif not isfootbody:
        # Footer contains </html> but not </body>
        # Note: webtabs.inc.php and feed.footer.php would be included here in PHP
        full_page += '</body>\n'
    else:
        # Footer contains </body> (and possibly </html>)
        # Note: webtabs.inc.php and feed.footer.php would be included here in PHP
        pass
    
    # #region agent log
    div_counts_final = _count_divs(full_page)
    _debug_log("content.py:wrap_content_with_header_footer", "Function exit", {
        "full_page_length": len(full_page),
        "div_counts": div_counts_final
    }, "B")
    # #endregion
    
    return full_page


def build_footer_wp(domainid: int, domain_data: Dict[str, Any], domain_settings: Dict[str, Any]) -> str:
    """
    Build footer HTML for WordPress plugin (feedit=2).
    Replicates seo_automation_build_footerWP function from ArticlesWP5.php
    """
    
    # Build link domain
    if domain_settings.get('usedurl') == 1 and domain_data.get('domain_url'):
        linkdomain = domain_data['domain_url'].rstrip('/')
    else:
        if domain_data.get('ishttps') == 1:
            linkdomain = 'https://'
        else:
            linkdomain = 'http://'
        
        if domain_data.get('usewww') == 1:
            linkdomain += 'www.' + domain_data['domain_name']
        else:
            linkdomain += domain_data['domain_name']
    
    # Get keywords
    keywords = get_domain_keywords(domainid)
    keywordcnt = len(keywords)
    
    if keywordcnt == 0:
        keywords = [domain_data['domain_name']]
    
    # Build footer HTML
    foot = ''
    num_lnks = 0
    
    # Get silo pages (bubblefeed entries)
    sql = """
        SELECT b.restitle, b.id, b.linkouturl, c.bubblefeedid, c.category, 
               b.resfulltext, b.resshorttext, b.NoContent,
               (SELECT COUNT(*) FROM bwp_link_placement WHERE showonpgid = b.id AND deleted != 1) AS links_per_page
        FROM bwp_bubblefeed b
        LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != '1'
        WHERE b.domainid = %s AND b.deleted != 1
        ORDER BY b.restitle
    """
    
    silo = db.fetch_all(sql, (domainid,))
    
    if silo:
        foot += '<li>'
        foot += '<ul class="seo-sub-nav">\n'
        
        for item in silo:
            import html
            is_bron_val = is_bron(domain_data.get('servicetype'))
            
            # Match PHP logic: elseif($silo[$i]['id'])
            if item.get('id'):
                # Build Resources link (Business Collective page - resfeedtext)
                # PHP condition: links_per_page >=1 || 1==1 (always true)
                if item.get('links_per_page', 0) >= 1 or True:  # Always true like PHP
                    if is_bron_val:
                        bclink = linkdomain + '/' + str(item['id']) + 'bc/'
                    else:
                        # Use toAscii(html_entity_decode(seo_text_custom(...))) for slug
                        slug_text = seo_text_custom(item['restitle'])  # seo_text_custom
                        slug_text = html.unescape(slug_text)  # html_entity_decode
                        slug_text = to_ascii(slug_text)  # toAscii
                        slug_text = slug_text.lower()  # strtolower
                        slug_text = slug_text.replace(' ', '-')  # str_replace(' ', '-', ...)
                        bclink = linkdomain + '/' + slug_text + '-' + str(item['id']) + 'bc/'
                    newsf = ' <a style="padding-left: 0px !important;" href="' + bclink + '">Resources</a>'
                else:
                    newsf = ''
                    bclink = ''
                
                # Main link logic (for resfulltext pages)
                # Check resourcesactive as string '1' or integer 1
                resourcesactive = str(domain_data.get('resourcesactive', ''))
                if resourcesactive == '1' or resourcesactive == 1:
                    # Resources active - show main article link (resfulltext) + Resources link (resfeedtext)
                    if (item.get('NoContent') == 0 or is_bron_val) and len(item.get('linkouturl', '').strip()) > 5:
                        # External link
                        foot += '<li><a style="padding-right: 0px !important;" href="' + item['linkouturl'] + '">' + clean_title(seo_filter_text_custom(item['restitle'])) + '</a>' + newsf + '</li>\n'
                    else:
                        # Internal link to main content page (resfulltext)
                        # Check if WordPress plugin or PHP plugin to use correct URL structure
                        wp_plugin = domain_data.get('wp_plugin', 0)
                        # #region agent log
                        _debug_log("content.py:build_footer_wp", "Building keyword link", {
                            "wp_plugin": wp_plugin,
                            "wp_plugin_type": type(wp_plugin).__name__,
                            "restitle": item.get('restitle', ''),
                            "item_id": item.get('id', '')
                        }, "A")
                        # #endregion
                        if wp_plugin == 1:
                            # WordPress plugin: use /slug-id/ format
                            slug_text = seo_text_custom(item['restitle'])  # seo_text_custom
                            slug_text = html.unescape(slug_text)  # html_entity_decode
                            slug_text = to_ascii(slug_text)  # toAscii
                            slug_text = slug_text.lower()  # strtolower
                            slug_text = slug_text.replace(' ', '-')  # str_replace(' ', '-', ...)
                            main_link = linkdomain + '/' + slug_text + '-' + str(item['id']) + '/'
                        else:
                            # PHP plugin: use ?Action=1&k=keyword&PageID=id format
                            keyword_slug = seo_filter_text_custom(item['restitle']).lower().replace(' ', '-')
                            main_link = linkdomain + '/?Action=1&k=' + keyword_slug + '&PageID=' + str(item['id'])
                        # #region agent log
                        _debug_log("content.py:build_footer_wp", "Generated keyword link", {
                            "main_link": main_link,
                            "wp_plugin": wp_plugin
                        }, "A")
                        # #endregion
                        foot += '<li><a style="padding-right: 0px !important;" href="' + main_link + '">' + clean_title(seo_filter_text_custom(item['restitle'])) + '</a>' + newsf + '</li>\n'
                else:
                    # Resources not active - show only Business Collective link (resfeedtext)
                    if not bclink:
                        # Build bclink if not already built
                        if is_bron_val:
                            bclink = linkdomain + '/' + str(item['id']) + 'bc/'
                        else:
                            slug_text = seo_text_custom(item['restitle'])
                            slug_text = html.unescape(slug_text)
                            slug_text = to_ascii(slug_text)
                            slug_text = slug_text.lower()
                            slug_text = slug_text.replace(' ', '-')
                            bclink = linkdomain + '/' + slug_text + '-' + str(item['id']) + 'bc/'
                    foot += '<li><a style="padding-right: 0px !important;" href="' + bclink + '">' + clean_title(seo_filter_text_custom(item['restitle'])) + '</a></li>\n'
                
                num_lnks += 1
            # Match PHP logic: elseif(strlen(trim($silo[$i]['linkouturl'])) > 5)
            elif len(item.get('linkouturl', '').strip()) > 5:
                # External link case - build Resources link if links_per_page >= 1
                if item.get('links_per_page', 0) >= 1:
                    # Use seo_filter_text_custom for this case (line 235 in PHP)
                    slug_text = seo_filter_text_custom(item['restitle'])
                    slug_text = html.unescape(slug_text)
                    slug_text = to_ascii(slug_text)
                    slug_text = slug_text.lower()
                    slug_text = slug_text.replace(' ', '-')
                    bclink = linkdomain + '/' + slug_text + '-' + str(item.get('id', '')) + 'bc/'
                    newsf = ' <a style="padding-left: 0px !important;" href="' + bclink + '">Resources</a>'
                else:
                    newsf = ''
                foot += '<li><a style="padding-right: 0px !important;" href="' + item['linkouturl'] + '">' + clean_title(seo_filter_text_custom(item['restitle'])) + '</a>' + newsf + '</li>\n'
                num_lnks += 1
        
        foot += '</ul>\n'
        foot += 'Articles</li>\n'
    
    # Add Blog and FAQ links if configured
    if domain_settings.get('blogUrl') and len(domain_settings['blogUrl']) > 10:
        foot += '<li><a class="url" style="width: 100%;font-size:12px;line-height:13px;" target="_blank" href="' + domain_settings['blogUrl'] + '">Blog</a></li>\n'
    
    if domain_settings.get('faqUrl') and len(domain_settings['faqUrl']) > 10:
        foot += '<li><a class="url" style="width: 100%;font-size:12px;line-height:13px;" target="_blank" href="' + domain_settings['faqUrl'] + '">FAQ</a></li>\n'
    
    # Add "Recent Post" section (drip content links) if conditions are met
    servicetype = domain_data.get('servicetype')
    dripcontent = domain_data.get('dripcontent', 0)
    if servicetype not in [10, 356] and dripcontent > 3:
        bubba_sql = """
            SELECT ba.* 
            FROM bwp_bubbafeed ba
            LEFT JOIN bwp_bubblefeed bb ON bb.id = ba.bubblefeedid
            WHERE ba.domainid = %s
            AND ba.deleted != 1
            AND bb.deleted != 1
            AND LENGTH(ba.resfulltext) > 300
            ORDER BY ba.id DESC
            LIMIT 20
        """
        allbubba = db.fetch_all(bubba_sql, (domainid,))
        
        if allbubba:
            foot += '<li>'
            foot += '<ul class="seo-sub-nav">\n'
            import html
            for bubba in allbubba:
                # Use toAscii(html_entity_decode(seo_text_custom(...))) for slug
                slug_text = seo_text_custom(bubba.get('bubbatitle', ''))  # seo_text_custom
                slug_text = html.unescape(slug_text)  # html_entity_decode
                slug_text = to_ascii(slug_text)  # toAscii
                slug_text = slug_text.lower()  # strtolower
                slug_text = slug_text.replace(' ', '-')  # str_replace(' ', '-', ...)
                slug = slug_text + '-' + str(bubba['id']) + 'dc'
                bubba_title = clean_title(html.unescape(seo_filter_text_custom(bubba.get('bubbatitle', ''))))
                foot += '<li><a style="padding-right: 0px !important;" href="' + linkdomain + '/' + slug + '">' + bubba_title + '</a></li>\n'
            foot += '</ul>\n'
            foot += 'Recent Post</li>\n'
    
    # Build final footer HTML
    if domain_data.get('wr_name'):
        ltest = domain_data['wr_name']
    else:
        ltest = domain_data['domain_name']
    
    foot += '</ul><a href="' + linkdomain + '/"><div class="seo-button-paid">&copy; ' + str(datetime.now().year) + ' ' + ltest + '</div></a></li></ul>\n'
    
    # Prepend wrapper divs (matching PHP structure)
    footer_html = '<div class="seo-automation-spacer"></div>\n'
    footer_html += '<div style="display:block !important;" class="seo-footer-section ">\n'
    footer_html += '<ul class="seo-footer-nav num-lite">\n'
    footer_html += '<li>\n'
    footer_html += '<ul>\n'
    footer_html += foot
    footer_html += '<div class="seo-automation-spacer"></div>\n'
    footer_html += '<style>\n'
    footer_html += '.seo-footer-nav li ul li ul {\n'
    footer_html += '\tleft:70px !important;;\n'
    footer_html += '}\n'
    footer_html += '</style>\n'
    footer_html += '</div>'
    
    # Return the footer HTML (will be JSON-encoded and HTML-escaped in the route handler)
    return footer_html


def get_domain_keywords(domainid: int) -> list:
    """Get domain keywords (equivalent to PHP DomainKeywords function)."""
    sql = "SELECT keywords FROM bwp_domains WHERE id = %s"
    result = db.fetch_row(sql, (domainid,))
    if result and result.get('keywords'):
        keywords = [k.strip() for k in result['keywords'].split(',') if k.strip() and k.strip() != 'one way links']
        return keywords
    return []


def get_domain_keywords_from_bubblefeed(domainid: int, displayorder: int = 0) -> list:
    """
    Get domain keywords from bwp_bubblefeed (equivalent to PHP DomainKeywords function).
    PHP: DomainKeywords($domainid, $displayorder=0)
    Returns array of lowercase trimmed restitle values.
    """
    if displayorder:
        sql = """
            SELECT restitle FROM bwp_bubblefeed 
            WHERE domainid = %s AND deleted != 1 
            ORDER BY CASE WHEN active = 1 THEN 0 ELSE 1 END, restitle
        """
    else:
        sql = """
            SELECT restitle FROM bwp_bubblefeed 
            WHERE domainid = %s AND deleted != 1 
            ORDER BY createdDate
        """
    restitles = db.fetch_all(sql, (domainid,))
    keywords = [str(row['restitle']).lower().strip() for row in restitles if row.get('restitle')]
    return keywords


def seo_filter_text_custom(text: str) -> str:
    """Clean text similar to PHP seo_filter_text_custom."""
    import re
    if text is None:
        return ''
    text = str(text).strip()
    text = re.sub(r'&(amp;)+', '&', text)
    text = text.replace('&amp;amp;', '&amp;')
    text = text.replace('&amp;mdash;', '&mdash;')
    text = text.replace('&amp;nbsp;', '&nbsp;')
    text = text.replace('&amp;#', '&#')
    text = text.replace("&#39;", "'")
    text = text.replace("&#124;", "|")
    text = text.replace("&gt;", ">")
    text = text.replace("&lt;", "<")
    text = text.replace('&Acirc;', ' ')
    text = text.replace('&acirc;', '')
    text = text.replace('&#128;', '')
    text = text.replace('&#153;', '')
    text = text.replace("&rsquo;", "'")
    text = text.replace("&bull;", " ")
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&ndash;', '-')
    text = text.replace('&ldquo;', '"')
    text = text.replace('&rdquo;', '"')
    text = text.replace('&mdash;', '--')
    return text


def seo_text_custom(text: str) -> str:
    """Clean text similar to PHP seo_text_custom."""
    import re
    if text is None:
        return ''
    text = str(text).strip()
    text = re.sub(r'&(amp;)+', '&', text)
    text = text.replace("&#39;", "'")
    text = text.replace("&#124;", "|")
    text = text.replace(":", "")
    text = text.replace("'", "")
    return text


def seo_filter_text_customapi(text: str) -> str:
    """Clean text similar to PHP seo_filter_text_customapi (for API output)."""
    import re
    text = text.strip()
    text = re.sub(r'&(amp;)+', '&', text)
    text = text.replace('&amp;amp;', '&amp;')
    text = text.replace('&amp;mdash;', '&mdash;')
    text = text.replace('&amp;nbsp;', '&nbsp;')
    text = text.replace('&amp;#', '&#')
    # Note: Does NOT decode &#39; and &#124; (commented out in PHP)
    return text


def trim_to_first_n_words(text: str, n: int) -> str:
    """Trim text to first N words (PHP bwp_shorten_string)."""
    words = text.split()
    if len(words) <= n:
        return text
    return ' '.join(words[:n]) + ' ...'


def to_ascii(text: str) -> str:
    """Convert text to ASCII (simplified version of PHP toAscii).
    Note: PHP toAscii expects text to already be processed by seo_text_custom and html_entity_decode.
    """
    import re
    if text is None:
        return ''
    # Text should already be processed by seo_text_custom and html_entity_decode before calling this
    text = str(text).replace(' &#x26;', '')
    # Basic transliteration (simplified - full version has extensive table)
    text = text.replace("'", "")
    text = text.replace('#039;', '')
    text = text.replace(' & ', ' ')
    text = text.replace('&', '')
    return text


def seo_slug(text: str) -> str:
    """Convert text to SEO-friendly slug."""
    import re
    # Use to_ascii and then convert to slug
    text = to_ascii(text)
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text.strip())
    return text


def _has_capitalization(text: str) -> bool:
    """
    Check if a string already contains any uppercase letters.
    Returns True if the string has any uppercase letters, False otherwise.
    """
    if not text:
        return False
    return any(c.isupper() for c in text)


def clean_title(text: str) -> str:
    """Clean title for display (simplified version of seo_automation_clean_title)."""
    if text is None:
        return ''
    text = str(text)
    text_stripped = text.strip()
    
    # Check if text already has capitalization - if so, return as-is
    if _has_capitalization(text_stripped):
        return text_stripped
    
    text_lower = text_stripped.lower()
    if text_stripped == text_lower:
        # Title case
        return text_stripped.title()
    else:
        return text_stripped


def custom_ucfirst_words(text: str) -> str:
    """Capitalize first letter of each word (PHP customUcfirstWords)."""
    if not text:
        return ''
    
    # Check if text already has capitalization - if so, return as-is
    if _has_capitalization(text):
        return text
    
    words = text.split()
    return ' '.join(word.capitalize() for word in words)


def seo_text_customamp(text: str) -> str:
    """Clean text similar to PHP seo_text_customamp."""
    text = text.replace("&amp;amp;", "&amp;")
    text = text.replace("&amp;amp;", "&amp;")
    return text


def seo_automation_add_text_link_new(text: str = '', kword: str = '', iurl: str = '', follow: str = '', title: str = '') -> str:
    """
    Add text link to content (PHP seo_automation_add_text_link_new).
    Replicates PHP function from functions.inc.php line 2273-2307.
    Skips first 4000 characters before searching for keyword.
    """
    import re
    import html
    
    if text and kword and iurl:
        # Clean keyword and text
        kword_clean = clean_title(kword)
        text = seo_text_customamp(text)
        
        # Skip the first 4000 characters (PHP line 2278-2280)
        initial_text = text[:4000]
        remaining_text = text[4000:]
        
        # Pattern to skip existing <a> tags and HTML tags, match keyword
        # PHP: /<a\b[^>]*>.*?<\/a>(*SKIP)(*FAIL)|<[^>]+>(*SKIP)(*FAIL)|\b{keyword}\b/i
        escaped_kword = re.escape(kword_clean)
        pattern = rf'(?:<a\b[^>]*>.*?</a>|<[^>]+>|\b{escaped_kword}\b)'
        
        replaced = False
        
        def replace_callback(match):
            nonlocal replaced
            match_str = match.group(0)
            # Check if this is the keyword (not an HTML tag)
            if not match_str.startswith('<') and match_str.lower() == kword_clean.lower():
                if not replaced:
                    replaced = True
                    title_attr = html.escape(title) if title else html.escape(kword_clean)
                    return f' <a title="{title_attr}" {follow} href="{iurl}">{match_str}</a>'
            return match_str
        
        remaining_text = re.sub(pattern, replace_callback, remaining_text, flags=re.IGNORECASE)
        
        # If no replacement was made, append link at end (PHP line 2297-2298)
        if not replaced:
            title_attr = html.escape(title) if title else html.escape(kword_clean)
            remaining_text = remaining_text + f' <a title="{title_attr}" {follow} href="{iurl}">{kword_clean}</a>'
        
        return initial_text + remaining_text
    else:
        return text


def seo_automation_add_text_link_newbc(text: str = '', kword: str = '', iurl: str = '', follow: str = '', title: str = '') -> str:
    """
    Add text link to content (PHP seo_automation_add_text_link_newbc).
    Replicates PHP function from functions.inc.php line 2309-2340.
    """
    import re
    import html
    
    if text and kword and iurl:
        # Clean keyword and text
        kword_clean = clean_title(kword)
        text = seo_text_customamp(text)
        
        # Pattern to skip existing <a> tags and HTML tags, match keyword
        # PHP: /<a\b[^>]*>.*?<\/a>(*SKIP)(*FAIL)|<[^>]+>(*SKIP)(*FAIL)|\b{keyword}\b/i
        escaped_kword = re.escape(kword_clean)
        pattern = rf'(?:<a\b[^>]*>.*?</a>|<[^>]+>|\b{escaped_kword}\b)'
        
        replaced = False
        
        def replace_callback(match):
            nonlocal replaced
            match_str = match.group(0)
            # Check if this is the keyword (not an HTML tag)
            if not match_str.startswith('<') and match_str.lower() == kword_clean.lower():
                if not replaced:
                    replaced = True
                    title_attr = html.escape(title) if title else html.escape(kword_clean)
                    return f' <a title="{title_attr}" {follow} target="_blank" href="{iurl}">{match_str}</a>'
            return match_str
        
        text = re.sub(pattern, replace_callback, text, flags=re.IGNORECASE)
        
        # If no replacement was made, append link at end
        if not replaced:
            title_attr = html.escape(title) if title else html.escape(kword_clean)
            text = text + f' <a title="{title_attr}" {follow} target="_blank" href="{iurl}">{kword_clean}</a>'
        
        return text
    else:
        return text


def link_keywords_in_content(
    content: str,
    main_keyword: str,
    main_keyword_url: str,
    supporting_keywords: list,
    supporting_keyword_urls: list,
    append_unfound: bool = True
) -> str:
    """
    Link keywords in content and append unfound keywords at the end.
    This function replaces seo_automation_add_text_link_new for keyword linking.
    
    For each keyword:
    - If found in content (outside of <a> tags and HTML tags), wrap it with <a> tag (max 2 per keyword)
    - If not found, add to unfound list
    - At the end, append all unfound keywords as links, separated by <br>
    
    Args:
        content: HTML content to process
        main_keyword: Main keyword text
        main_keyword_url: URL for main keyword (homepage)
        supporting_keywords: List of supporting keyword texts (max 2)
        supporting_keyword_urls: List of URLs for supporting keywords
        append_unfound: If True, append unfound keywords as links at the end (only used for resfulltext)
    
    Returns:
        Content with keywords linked in-content and unfound keywords appended at the end
    """
    import html
    import re
    
    # #region agent log
    _debug_log("content.py:link_keywords_in_content", "Function entry", {
        "main_keyword": main_keyword,
        "supporting_keywords_count": len(supporting_keywords) if supporting_keywords else 0,
        "append_unfound": append_unfound,
        "content_length": len(content) if content else 0
    }, "A")
    # #endregion
    
    if not content:
        return content
    
    # Limit supporting keywords to 2
    supporting_keywords = supporting_keywords[:2] if supporting_keywords else []
    supporting_keyword_urls = supporting_keyword_urls[:2] if supporting_keyword_urls else []
    
    # Ensure we have URLs for all supporting keywords
    while len(supporting_keyword_urls) < len(supporting_keywords):
        supporting_keyword_urls.append('')
    
    # Build list of keywords to process (main keyword first, then supporting)
    keywords_to_process = []
    if main_keyword and main_keyword_url:
        keywords_to_process.append({
            'text': main_keyword,
            'url': main_keyword_url,
            'is_main': True
        })
    
    for i, supp_kw in enumerate(supporting_keywords):
        if supp_kw and i < len(supporting_keyword_urls) and supporting_keyword_urls[i]:
            keywords_to_process.append({
                'text': supp_kw,
                'url': supporting_keyword_urls[i],
                'is_main': False
            })
    
    # #region agent log
    _debug_log("content.py:link_keywords_in_content", "Keywords to process", {
        "keywords_to_process": [kw.get('text') for kw in keywords_to_process],
        "keywords_count": len(keywords_to_process)
    }, "A")
    # #endregion
    
    if not keywords_to_process:
        return content
    
    # Process content: link keywords found in content (max 2 per keyword)
    result = content
    
    # For main keyword: skip first 4000 characters (like seo_automation_add_text_link_new)
    # For supporting keywords: process entire content
    for kw_data in keywords_to_process:
        kw_text = kw_data['text']
        kw_url = kw_data['url']
        is_main = kw_data.get('is_main', False)
        
        if not kw_text or not kw_url:
            continue
        
        kw_clean = clean_title(kw_text)
        escaped_kword = re.escape(kw_clean)
        
        if is_main:
            # Skip first 4000 characters for main keyword
            initial_text = result[:4000]
            text_to_process = result[4000:]
        else:
            initial_text = ''
            text_to_process = result
        
        # Find all HTML tags and existing <a> tags to build forbidden ranges
        # This prevents linking keywords inside tags or existing links
        forbidden_ranges = []
        
        # Find all <a> tags (including nested content)
        for match in re.finditer(r'<a\b[^>]*>.*?</a>', text_to_process, re.IGNORECASE | re.DOTALL):
            forbidden_ranges.append((match.start(), match.end()))
        
        # Find all HTML tags (opening, closing, self-closing)
        for match in re.finditer(r'<[^>]+>', text_to_process):
            forbidden_ranges.append((match.start(), match.end()))
        
        # Find all keyword matches (case-insensitive)
        links_created = 0
        max_links_per_keyword = 2
        
        def replace_callback(match):
            nonlocal links_created
            if links_created >= max_links_per_keyword:
                return match.group(0)
            
            match_start = match.start()
            match_end = match.end()
            
            # Check if this match is in a forbidden range
            for forbidden_start, forbidden_end in forbidden_ranges:
                if match_start >= forbidden_start and match_end <= forbidden_end:
                    return match.group(0)  # Skip this match
            
            # This is a valid match - wrap it with <a> tag
            links_created += 1
            title_attr = html.escape(kw_clean)
            url_attr = html.escape(kw_url)
            return f' <a title="{title_attr}" href="{url_attr}">{match.group(0)}</a>'
        
        # Pattern to match keyword (word boundaries, case-insensitive)
        pattern = rf'\b{escaped_kword}\b'
        processed_text = re.sub(pattern, replace_callback, text_to_process, flags=re.IGNORECASE)
        
        if is_main:
            result = initial_text + processed_text
        else:
            result = processed_text
    
    # Now check for unfound keywords (only if append_unfound is True)
    if append_unfound:
        # Remove <a> tags and their content before searching for unfound keywords
        content_without_links = re.sub(r'<a\b[^>]*>.*?</a>', '', result, flags=re.IGNORECASE | re.DOTALL)
        
        # Strip remaining HTML tags for case-insensitive keyword search
        content_text = re.sub(r'<[^>]+>', '', content_without_links)
        
        # #region agent log
        _debug_log("content.py:link_keywords_in_content", "Content text (stripped HTML and links) for unfound check", {
            "content_text_length": len(content_text),
            "content_text_preview": content_text[:200] if content_text else ""
        }, "A")
        # #endregion
        
        # Check which keywords are NOT found in the content (case-insensitive)
        unfound_keywords = []
        for kw_data in keywords_to_process:
            kw_text = kw_data['text']
            if not kw_text:
                continue
            
            # Case-insensitive search for the keyword in plain text content
            pattern = re.escape(kw_text)
            found = bool(re.search(pattern, content_text, re.IGNORECASE))
            
            # #region agent log
            _debug_log("content.py:link_keywords_in_content", "Keyword search result for unfound check", {
                "keyword": kw_text,
                "found": found
            }, "A")
            # #endregion
            
            if not found:
                unfound_keywords.append(kw_data)
        
        # #region agent log
        _debug_log("content.py:link_keywords_in_content", "Unfound keywords", {
            "unfound_keywords": [kw.get('text') for kw in unfound_keywords],
            "unfound_count": len(unfound_keywords)
        }, "A")
        # #endregion
        
        # Append unfound keyword links at the end, separated by <br>
        if unfound_keywords:
            keyword_links = []
            for kw_data in unfound_keywords:
                kw_text = kw_data['text']
                kw_url = kw_data['url']
                
                if not kw_text or not kw_url:
                    continue
                
                title_attr = html.escape(kw_text)
                url_attr = html.escape(kw_url)
                link_html = f'<a title="{title_attr}" href="{url_attr}">{kw_text}</a>'
                keyword_links.append(link_html)
            
            if keyword_links:
                # Join links with <br> separator
                links_html = '<br>'.join(keyword_links)
                result = result + '<br><br>' + links_html
                
                # #region agent log
                _debug_log("content.py:link_keywords_in_content", "Appended unfound links", {
                    "links_html": links_html,
                    "links_count": len(keyword_links),
                    "result_length": len(result)
                }, "A")
                # #endregion
    
    # #region agent log
    _debug_log("content.py:link_keywords_in_content", "Function exit", {
        "final_content_length": len(result)
    }, "A")
    # #endregion
    
    return result


def insert_after_first_heading(html_string: str, string_to_insert: str) -> str:
    """
    Insert string after the second heading tag (PHP insertAfterFirstHeading).
    Replicates PHP function from functions.inc.php line 151-178.
    """
    import re
    
    heading_count = 0
    replace_count = 0
    
    def replace_callback(match):
        nonlocal heading_count, replace_count
        heading_count += 1
        
        # If this is the second heading tag, append the string to insert
        if heading_count == 2:
            replace_count = 1
            return string_to_insert + match.group(0)
        
        # Return the original heading tag for all other cases
        return match.group(0)
    
    # Pattern to match heading tags: <h1> through <h6>
    pattern = r'<h[1-6][^>]*>.*?</h[1-6]>'
    result = re.sub(pattern, replace_callback, html_string, flags=re.IGNORECASE | re.DOTALL)
    
    # If no replacement was made, prepend the string (PHP line 176)
    if replace_count == 0:
        result = string_to_insert + result
    
    return result


def check_image_src_gpt(string: str) -> int:
    """
    Check if string contains specific image src pattern (PHP checkImageSrcGPT).
    Replicates PHP function from functions.inc.php line 180-192.
    Returns 1 if pattern NOT found, 0 if found.
    """
    import re
    
    # Regular expression to find <img> tags with a specific src
    pattern = r'<img[^>]+src\s*=\s*["\']https://services6\.imagehosting\.space/images/[^"\']+["\'][^>]*>'
    
    # Check if the pattern is found in the string
    if re.search(pattern, string, re.IGNORECASE):
        # If found, return 0
        return 0
    
    # If not found, return 1
    return 1


def is_bron(servicetype: Optional[int]) -> bool:
    """Check if service type is BRON, matching PHP isBRON function."""
    if servicetype is None:
        return False
    # Convert to int to match PHP (int)$servicetype
    try:
        servicetype_int = int(servicetype)
    except (ValueError, TypeError):
        return False
    if servicetype_int == 0:
        return False
    # Use %% to escape % for PyMySQL (which uses Python % formatting)
    # PHP: servicetype LIKE 'BRON %' (with space after BRON)
    sql = "SELECT * FROM bwp_services WHERE servicetype LIKE 'BRON %%' AND servicetype != 'SEOM 5' AND id = %s ORDER BY keywords"
    result = db.fetch_all(sql, (servicetype_int,))
    return bool(result)


def is_seom(servicetype: Optional[int]) -> bool:
    """Check if service type is SEOM, matching PHP isSEOM function."""
    if servicetype is None:
        return False
    # Convert to int to match PHP (int)$servicetype
    try:
        servicetype_int = int(servicetype)
    except (ValueError, TypeError):
        return False
    if servicetype_int == 0:
        return False
    # Use %% to escape % for PyMySQL (which uses Python % formatting)
    # PHP: servicetype LIKE 'SEOM %' (with space after SEOM)
    sql = "SELECT * FROM bwp_services WHERE servicetype LIKE 'SEOM %%' AND servicetype != 'SEOM 5' AND id = %s ORDER BY keywords"
    result = db.fetch_all(sql, (servicetype_int,))
    return bool(result)


def strip_html(text: str) -> str:
    """Strip HTML tags from text."""
    from html.parser import HTMLParser
    class MLStripper(HTMLParser):
        def __init__(self):
            super().__init__()
            self.reset()
            self.strict = False
            self.convert_charrefs = True
            self.fed = []
        def handle_data(self, d):
            self.fed.append(d)
        def get_data(self):
            return ''.join(self.fed)
    s = MLStripper()
    s.feed(text)
    return s.get_data()


def build_excerpt(text: str, max_words: int = 20) -> str:
    """Build excerpt from text (first N words)."""
    if not text or len(text) < 50:
        return ''
    import re
    import html
    # Clean content
    content = re.sub(r'Table of Contents\s+', '', text)
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\r|\n', ' ', content)
    content = html.unescape(content)
    content = seo_filter_text_custom(content)
    content = strip_html(content)
    words = content.split()[:max_words]
    return ' '.join(words) + '... ' if words else ''


def build_pages_array(domainid: int, domain_data: Dict[str, Any], domain_settings: Dict[str, Any], template_file: Optional[str] = None) -> list:
    """
    Build pages array for WordPress plugin (feedit=1).
    Returns array of page objects matching PHP format.
    """
    pagesarray = []
    servicetype = domain_data.get('servicetype')
    
    # 1. Get bubblefeed entries (main pages)
    if domain_data.get('resourcesactive'):
        sql = """
            SELECT b.*, c.category AS bubblecat, c.bubblefeedid AS bubblecatid, c.id AS bubblecatsid
            FROM bwp_bubblefeed b
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
            WHERE b.active = 1 AND b.domainid = %s AND b.deleted != 1
        """
        page_ex = db.fetch_all(sql, (domainid,))
        
        for page in page_ex:
            if not is_bron(servicetype) or len(page.get('linkouturl', '')) < 5:
                pageid = page['id']
                keyword = clean_title(seo_filter_text_custom(page['restitle']))
                
                # Build meta title and keywords
                if page.get('metatitle') and page['metatitle'].strip():
                    metaTitle = clean_title(seo_filter_text_custom(page['metatitle']))
                    metaKeywords = seo_filter_text_custom(page['restitle']).lower()
                    if page.get('bubblecat'):
                        bubbles_sql = "SELECT restitle FROM bwp_bubblefeed WHERE domainid = %s AND categoryid = %s"
                        bubbles = db.fetch_all(bubbles_sql, (domainid, page.get('categoryid')))
                        for bub in bubbles:
                            if bub['restitle'] != page['restitle']:
                                metaKeywords += ', ' + seo_filter_text_custom(bub['restitle']).lower()
                else:
                    metaTitle = clean_title(seo_filter_text_custom(page['restitle']))
                    metaKeywords = seo_filter_text_custom(page['restitle']).lower()
                    if page.get('bubblecat'):
                        bubbles_sql = "SELECT restitle FROM bwp_bubblefeed WHERE domainid = %s AND categoryid = %s"
                        bubbles = db.fetch_all(bubbles_sql, (domainid, page.get('categoryid')))
                        for bub in bubbles:
                            if bub['restitle'] != page['restitle']:
                                metaTitle += ' - ' + clean_title(seo_filter_text_custom(bub['restitle']))
                                metaKeywords += ', ' + seo_filter_text_custom(bub['restitle']).lower()
                    
                    if len(domain_data.get('wr_phone', '')) > 9 and domain_settings.get('phoneintitle') == 1:
                        metaTitle = domain_data['wr_phone'] + ' - ' + metaTitle
                
                # Build excerpt
                if page.get('metadescription') and page['metadescription'].strip():
                    sorttext = seo_filter_text_custom(page['metadescription'])
                    words = sorttext.split()[:20]
                    sorttext = ' '.join(words) + '... '
                else:
                    sorttext = build_excerpt(page.get('resfulltext', ''))
                
                sorttext = strip_html(seo_filter_text_custom(sorttext))
                slug = seo_slug(keyword) + '-' + str(pageid) + '/'
                
                # Convert datetime to string if needed
                post_date = page.get('createdDate', '')
                if post_date and hasattr(post_date, 'strftime'):
                    post_date = post_date.strftime('%Y-%m-%d %H:%M:%S')
                elif post_date is None:
                    post_date = ''
                
                pagearray = {
                    'pageid': str(pageid),
                    'post_title': keyword,
                    'canonical': '',
                    'post_type': 'page',
                    'post_content': '',
                    'comment_status': 'closed',
                    'ping_status': 'closed',
                    'post_date': str(post_date),
                    'post_excerpt': sorttext,
                    'post_name': slug,
                    'post_status': 'publish',
                    'post_metatitle': metaTitle,
                    'post_metakeywords': metaKeywords,
                    'template_file': template_file or ''
                }
                pagesarray.append(pagearray)
    
    # 2. Get bubblefeedsupport entries (support pages) - only for SEOM/BRON
    if is_seom(servicetype) or is_bron(servicetype):
        sql = """
            SELECT ba.id, ba.restitle, ba.resshorttext, ba.resfulltext, ba.createdDate, ba.metatitle, ba.metadescription
            FROM bwp_bubblefeedsupport ba
            LEFT JOIN bwp_bubblefeed bb ON bb.id = ba.bubblefeedid
            WHERE ba.active = 1 AND ba.domainid = %s
            AND CHAR_LENGTH(ba.resfulltext) > 300
            AND bb.active = 1
            AND ba.deleted != 1
            AND bb.deleted != 1
        """
        page_exs = db.fetch_all(sql, (domainid,))
        
        for page in page_exs:
            pageid = page['id']
            keyword = clean_title(seo_filter_text_custom(page['restitle']))
            
            if page.get('metatitle') and page['metatitle'].strip():
                metaTitle = clean_title(seo_filter_text_custom(page['metatitle']))
                metaKeywords = seo_filter_text_custom(page['restitle']).lower()
            else:
                metaTitle = clean_title(seo_filter_text_custom(page['restitle']))
                metaKeywords = seo_filter_text_custom(page['restitle']).lower()
                if len(domain_data.get('wr_phone', '')) > 9 and domain_settings.get('phoneintitle') == 1:
                    metaTitle = domain_data['wr_phone'] + ' - ' + metaTitle
            
            # Build excerpt
            if page.get('metadescription') and page['metadescription'].strip():
                sorttext = seo_filter_text_custom(page['metadescription'])
                words = sorttext.split()[:20]
                sorttext = ' '.join(words) + '... '
            else:
                sorttext = build_excerpt(page.get('resfulltext', ''))
            
            sorttext = strip_html(seo_filter_text_custom(sorttext))
            slug = seo_slug(keyword) + '-' + str(pageid) + '/'
            
            # Convert datetime to string if needed
            post_date = page.get('createdDate', '')
            if post_date and hasattr(post_date, 'strftime'):
                post_date = post_date.strftime('%Y-%m-%d %H:%M:%S')
            elif post_date is None:
                post_date = ''
            
            pagearray = {
                'pageid': str(pageid),
                'canonical': '',
                'post_title': keyword,
                'post_type': 'page',
                'post_content': '',
                'comment_status': 'closed',
                'ping_status': 'closed',
                'post_date': str(post_date),
                'post_excerpt': sorttext,
                'post_name': slug,
                'post_status': 'publish',
                'post_metatitle': clean_title(seo_filter_text_custom(metaTitle)),
                'post_metakeywords': seo_filter_text_custom(page['restitle']).lower(),
                'template_file': template_file or ''
            }
            pagesarray.append(pagearray)
    
    # 3. Get business collective pages (bc pages)
    sql = """
        SELECT b.*
        FROM bwp_bubblefeed b
        WHERE b.active = 1 AND b.domainid = %s AND b.deleted != 1
    """
    bcpage_ex = db.fetch_all(sql, (domainid,))
    
    for bcpage in bcpage_ex:
        pageid = bcpage['id']
        if len(bcpage.get('resfeedtext', '')) > 50:
            sorttext = seo_filter_text_custom(bcpage['resfeedtext'])
            import html
            sorttext = html.unescape(sorttext)
            sorttext = strip_html(sorttext)
            words = sorttext.split()[:20]
            sorttext = ' '.join(words) + '... '
        else:
            sorttext = ''
        
        keyword = clean_title(seo_filter_text_custom(bcpage['restitle']))
        
        if is_bron(servicetype):
            slug = str(pageid) + 'bc/'
            metaTitle = domain_data['domain_name'] + ' - ' + str(pageid) + ' - Resources'
            keyword = domain_data['domain_name'] + ' - ' + str(pageid)
        else:
            slug = seo_slug(keyword) + '-' + str(pageid) + 'bc/'
            metaTitle = keyword.lower() + ' - Resources'
        
        sorttext = strip_html(seo_filter_text_custom(sorttext))
        
        if len(domain_data.get('wr_phone', '')) > 9 and domain_settings.get('phoneintitle') == 1:
            metaTitle = domain_data['wr_phone'] + ' - ' + metaTitle
        
        # Convert datetime to string if needed
        post_date = bcpage.get('createdDate', '')
        if post_date and hasattr(post_date, 'strftime'):
            post_date = post_date.strftime('%Y-%m-%d %H:%M:%S')
        elif post_date is None:
            post_date = ''
        
        bcpagearray = {
            'pageid': str(pageid) + 'bc',
            'post_title': keyword.lower() + ' - Resources',
            'post_type': 'page',
            'post_content': '',
            'comment_status': 'closed',
            'ping_status': 'closed',
            'post_date': str(post_date),
            'post_excerpt': sorttext,
            'post_name': slug,
            'post_status': 'publish',
            'post_metatitle': metaTitle,
            'post_metakeywords': keyword.lower() + ' Resources',
            'template_file': template_file or ''
        }
        pagesarray.append(bcpagearray)
    
    return pagesarray


def extract_youtube_video_id(video_url: str) -> str:
    """
    Extract YouTube video ID from various URL formats.
    Replicates the PHP video URL cleaning logic from websitereference-wp.php lines 366-383
    """
    import re
    if not video_url or not video_url.strip():
        return ""
    
    # Clean the video URL
    vid = str(video_url).strip()
    vid = vid.replace('https://www.', '')
    vid = vid.replace('http://www.', '')
    vid = vid.replace('http://', '')
    vid = vid.replace('//', '')
    vid = vid.replace('youtu.be/', '')
    vid = vid.replace('youtube.com/embed/', '')
    vid = vid.replace('youtube.com/watch?v=', '')
    vid = vid.replace('www.', '')
    
    # Remove &feature=... and similar parameters
    vid = re.sub(r'&.*feature.*', '', vid)
    vid = vid.strip()
    
    return vid


def build_page_wp(
    bubbleid: int,
    domainid: int,
    debug: bool,
    agent: str,
    keyword: str,
    domain_data: Dict[str, Any],
    domain_settings: Dict[str, Any],
    artpageid: int = 0,
    artdomainid: int = 0,
    support: int = 0,
    offpageid: int = 0,
    offdomainid: int = 0
) -> str:
    """
    Build Website Reference page HTML (Action=1).
    Replicates seo_automation_build_page from websitereference-wp.php
    """
    import html
    import re
    from urllib.parse import quote
    from datetime import datetime, timedelta
    import random
    
    # #region agent log
    _debug_log("content.py:build_page_wp", "Function entry", {
        "bubbleid": bubbleid,
        "domainid": domainid,
        "keyword": keyword,
        "bubbleid_is_falsy": not bubbleid,
        "domainid_is_falsy": not domainid
    }, "A")
    # #endregion
    logger.info(f"build_page_wp entry: bubbleid={bubbleid}, domainid={domainid}, keyword={keyword}")
    
    if not bubbleid or not domainid:
        # #region agent log
        _debug_log("content.py:build_page_wp", "Early return: bubbleid or domainid is falsy", {
            "bubbleid": bubbleid,
            "domainid": domainid
        }, "A")
        # #endregion
        logger.warning(f"build_page_wp early return: bubbleid={bubbleid}, domainid={domainid}")
        return ""
    
    # Get bubblefeed data - handle multiple scenarios (PHP lines 52-108)
    res = None
    if offpageid != 0 and support != 1:
        sql = """
            SELECT bo.id, bo.bubblefeedid, b.restitle, bo.title, bo.resfulltext, b.resshorttext, 
                   b.linkouturl, b.resaddress, b.resgooglemaps, b.resphone, bo.resvideo, 
                   b.resvideo AS resvideobubble, b.resname,
                   IFNULL(c.id, '') AS categoryid, IFNULL(c.category, '') AS category
            FROM bwp_bubblefeedoffsite bo
            LEFT JOIN bwp_bubblefeed b ON b.id = bo.bubblefeedid
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
            WHERE bo.id = %s AND bo.domainid = %s
        """
        res = db.fetch_row(sql, (offpageid, offdomainid))
    elif support == 1 and (is_seom(domain_data.get('servicetype')) or is_bron(domain_data.get('servicetype'))):
        sql = """
            SELECT b.restitle, b.title, b.resfulltext, b.resshorttext, b.linkouturl, b.resaddress, 
                   b.resgooglemaps, b.resphone, b.resvideo, b.resname, b.bubblefeedid,
                   b.resgoogle, b.resfb, b.resx, b.reslinkedin, b.resinstagram, b.restiktok, b.respinterest,
                   IFNULL(c.id, '') AS categoryid, IFNULL(c.category, '') AS category
            FROM bwp_bubblefeedsupport b
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
            WHERE b.id = %s AND b.domainid = %s
        """
        res = db.fetch_row(sql, (bubbleid, domainid))
    elif artpageid != 0:
        sql = """
            SELECT b.id, b.restitle, b.title, b.resfulltext, b.resshorttext, b.linkouturl, 
                   b.resaddress, b.resgooglemaps, b.resphone, b.resvideo, b.resname,
                   IFNULL(c.id, '') AS categoryid, IFNULL(c.category, '') AS category
            FROM bwp_bubblefeed b
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
            WHERE b.id = %s AND b.domainid = %s AND b.deleted != 1
        """
        res = db.fetch_row(sql, (artpageid, artdomainid))
    else:
        # Match PHP websitereference-wp.php line 88-89: No deleted check in first query
        sql = """
            SELECT b.id, b.restitle, b.title, b.resfulltext, b.resshorttext, b.linkouturl, 
                   b.categoryid AS bubblecategoryid, b.resphone, b.resvideo, b.resaddress, 
                   b.resgooglemaps, b.resname, b.resgoogle, b.resfb, b.resx, b.reslinkedin, 
                   b.resinstagram, b.restiktok, b.respinterest,
                   IFNULL(c.id, '') AS categoryid, IFNULL(c.category, '') AS category, 
                   IFNULL(c.bubblefeedid, '') AS bubblefeedid
            FROM bwp_bubblefeed b
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
            WHERE b.id = %s AND b.domainid = %s
        """
        logger.info(f"build_page_wp executing SQL: {sql[:200]}... with params: bubbleid={bubbleid}, domainid={domainid}")
        res = db.fetch_row(sql, (bubbleid, domainid))
        # #region agent log
        _debug_log("content.py:build_page_wp", "Main query by bubbleid result", {
            "bubbleid": bubbleid,
            "domainid": domainid,
            "res_found": res is not None,
            "res_id": res.get('id') if res else None
        }, "A")
        # #endregion
        logger.info(f"build_page_wp main query result: res_found={res is not None}, res_id={res.get('id') if res else None}")
        
        # PHP Article.php lines 722-730: If not found in bwp_bubblefeed and domain is SEOM or BRON, check bwp_bubblefeedsupport
        if not res:
            servicetype = domain_data.get('servicetype')
            if is_seom(servicetype) or is_bron(servicetype):
                support_sql = """
                    SELECT b.id, b.restitle, b.title, b.resfulltext, b.resshorttext, b.linkouturl, b.resaddress, 
                           b.resgooglemaps, b.resphone, b.resvideo, b.resname, b.bubblefeedid,
                           b.resgoogle, b.resfb, b.resx, b.reslinkedin, b.resinstagram, b.restiktok, b.respinterest,
                           IFNULL(c.id, '') AS categoryid, IFNULL(c.category, '') AS category
                    FROM bwp_bubblefeedsupport b
                    LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
                    WHERE b.id = %s AND b.domainid = %s
                """
                logger.info(f"build_page_wp checking bwp_bubblefeedsupport: bubbleid={bubbleid}, domainid={domainid}, servicetype={servicetype}")
                res = db.fetch_row(support_sql, (bubbleid, domainid))
                if res:
                    support = 1
                    logger.info(f"build_page_wp found in bwp_bubblefeedsupport: id={res.get('id') if res else None}, restitle={res.get('restitle') if res else None}")
                else:
                    logger.warning(f"build_page_wp not found in bwp_bubblefeedsupport either")
            
            # Diagnostic: Check if record exists at all (even if deleted)
            if not res:
                diag_sql = "SELECT id, domainid, deleted, restitle FROM bwp_bubblefeed WHERE id = %s"
                diag_res = db.fetch_row(diag_sql, (bubbleid,))
                logger.warning(f"build_page_wp diagnostic: Record with id={bubbleid} exists: {diag_res is not None}, if exists: domainid={diag_res.get('domainid') if diag_res else None}, deleted={diag_res.get('deleted') if diag_res else None}, restitle={diag_res.get('restitle') if diag_res else None}")
                
                # Check if keyword exists for this domain
                if keyword:
                    keyword_sql = "SELECT id, restitle, deleted FROM bwp_bubblefeed WHERE restitle = %s AND domainid = %s"
                    keyword_res = db.fetch_row(keyword_sql, (keyword, domainid))
                    logger.warning(f"build_page_wp diagnostic: Record with restitle='{keyword}' and domainid={domainid} exists: {keyword_res is not None}, if exists: id={keyword_res.get('id') if keyword_res else None}, deleted={keyword_res.get('deleted') if keyword_res else None}")
                
                # Check if pageid might be in bwp_bubbafeed
                bubba_sql = "SELECT id, domainid, deleted, bubbatitle FROM bwp_bubbafeed WHERE id = %s"
                bubba_res = db.fetch_row(bubba_sql, (bubbleid,))
                logger.warning(f"build_page_wp diagnostic: Record with id={bubbleid} in bwp_bubbafeed exists: {bubba_res is not None}, if exists: domainid={bubba_res.get('domainid') if bubba_res else None}, deleted={bubba_res.get('deleted') if bubba_res else None}, bubbatitle={bubba_res.get('bubbatitle') if bubba_res else None}")
    
    # Fallback: try to find by keyword (PHP lines 97-108)
    if not res and keyword:
        sql = """
            SELECT b.id, b.restitle, b.title, b.resfulltext, b.resshorttext, b.linkouturl, 
                   b.resphone, b.resvideo, b.resaddress, b.resgooglemaps, b.resname, b.NoContent,
                   b.resgoogle, b.resfb, b.resx, b.reslinkedin, b.resinstagram, b.restiktok, b.respinterest,
                   IFNULL(c.id, '') AS categoryid, IFNULL(c.category, '') AS category, 
                   IFNULL(c.bubblefeedid, '') AS bubblefeedid
            FROM bwp_bubblefeed b
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
            WHERE b.restitle = %s AND b.domainid = %s AND b.deleted != 1
        """
        res = db.fetch_row(sql, (keyword, domainid))
        # #region agent log
        _debug_log("content.py:build_page_wp", "Keyword fallback query result", {
            "keyword": keyword,
            "res_found": res is not None,
            "res_id": res.get('id') if res else None
        }, "A")
        # #endregion
    
    # #region agent log
    _debug_log("content.py:build_page_wp", "After all database queries", {
        "res_found": res is not None,
        "res_id": res.get('id') if res else None,
        "res_restitle": res.get('restitle') if res else None
    }, "A")
    # #endregion
    logger.info(f"build_page_wp after queries: res_found={res is not None}, res_id={res.get('id') if res else None}")
    
    if not res:
        # #region agent log
        _debug_log("content.py:build_page_wp", "Early return: res not found", {
            "bubbleid": bubbleid,
            "keyword": keyword,
            "domainid": domainid
        }, "A")
        # #endregion
        logger.warning(f"build_page_wp early return: res not found, bubbleid={bubbleid}, keyword={keyword}, domainid={domainid}")
        return ""
    
    # Build link domain (PHP lines 208-232)
    if domain_settings.get('usedurl') == 1 and domain_data.get('domain_url'):
        linkdomain = domain_data['domain_url'].rstrip('/')
    else:
        if domain_data.get('ishttps') == 1:
            linkdomain = 'https://'
        else:
            linkdomain = 'http://'
        if domain_data.get('usewww') == 1:
            linkdomain += 'www.' + domain_data['domain_name']
        else:
            linkdomain += domain_data['domain_name']
    
    # Build resurl (PHP lines 243-264)
    if artpageid != 0 or offpageid != 0:
        resurl = linkdomain
    else:
        if res.get('categoryid'):
            if res.get('bubblefeedid') == res.get('id'):
                resurl = '/'
            else:
                urltitle = seo_filter_text_custom(res.get('category', ''))
                slug_text = seo_text_custom(urltitle)
                slug_text = html.unescape(slug_text)
                slug_text = to_ascii(slug_text)
                slug_text = slug_text.lower()
                slug_text = slug_text.replace(' ', '-')
                resurl = linkdomain + '/' + slug_text + '-' + str(res.get('bubblefeedid', res.get('id', '')))
        elif is_seom(domain_data.get('servicetype')) and res.get('linkouturl'):
            resurl = res['linkouturl']
        else:
            resurl = '/'
    
    # Start building page (PHP line 136)
    # #region agent log
    _debug_log("content.py:build_page_wp", "Checking resourcesactive", {
        "resourcesactive": domain_data.get('resourcesactive'),
        "resourcesactive_is_1": domain_data.get('resourcesactive') == 1
    }, "A")
    # #endregion
    resourcesactive_val = domain_data.get('resourcesactive')
    logger.info(f"build_page_wp resourcesactive check: resourcesactive={resourcesactive_val}, is_1={resourcesactive_val == 1}")
    if resourcesactive_val != 1:
        # #region agent log
        _debug_log("content.py:build_page_wp", "Early return: resourcesactive != 1", {
            "resourcesactive": resourcesactive_val
        }, "A")
        # #endregion
        logger.warning(f"build_page_wp early return: resourcesactive != 1, value={resourcesactive_val}")
        return '<p>This feature is not available for your current package. Please upgrade your package. [ID-01]</p>'
    
    # #region agent log
    _debug_log("content.py:build_page_wp", "After resourcesactive check", {"proceeding": True}, "A")
    # #endregion
    
    # Get CSS class prefix based on wp_plugin
    css_prefix = get_css_class_prefix(domain_data.get('wp_plugin', 0))
    
    wpage = f'<div class="{css_prefix}-main-table" style="margin-left:auto;margin-right:auto;display:block;">\n'
    wpage += f'<div class="{css_prefix}-spacer"></div>\n'
    
    # #region agent log
    div_counts = _count_divs(wpage)
    _debug_log("content.py:build_page_wp", "After opening main div", {"wpage_length": len(wpage), "div_counts": div_counts}, "A")
    # #endregion
    
    # Check if resfulltext contains Bootstrap container classes and add Bootstrap CSS/JS if needed (PHP lines 266-275)
    resfulltext = res.get('resfulltext', '')
    if resfulltext and 'container justify-content-center' in resfulltext.lower():
        wpage += f'''
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@3.3.7/dist/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">

<script src="https://cdn.jsdelivr.net/npm/bootstrap@3.3.7/dist/js/bootstrap.min.js" integrity="sha384-Tc5IQib027qvyjSMfHjOMaLkfuWVxZxUPnCJA7l2mCWNIpG9mGCD8wGNIcPD7Txa" crossorigin="anonymous"></script>

<style>.wr-fulltext img {{height: auto !important;min-width:100%;}}@media (min-width: 992px){{.wr-fulltext img {{min-width:0;}}}}.container.justify-content-center {{max-width:100%;margin-bottom:15px;}}.{css_prefix}-spacer{{clear:both;}}.{css_prefix}-main-table h1:after, .{css_prefix}-main-table h2:after, .{css_prefix}-main-table h3:after, .{css_prefix}-main-table h4:after, .{css_prefix}-main-table h5:after, .{css_prefix}-main-table h6:after {{display: none !important;clear: none !important;}} .{css_prefix}-main-table h1, .{css_prefix}-main-table h2, .{css_prefix}-main-table h3, .{css_prefix}-main-table h4, .{css_prefix}-main-table h5, .{css_prefix}-main-table h6 {{clear: none !important;}}.{css_prefix}-main-table .row .col-md-6 {{	/* display:list-item; */ }} </style>
'''
    
    # Handle YouTube video embedding (PHP lines 282-465)
    # Priority: resvideo -> resvideobubble -> domain_data['wr_video']
    video_id = ""
    if res.get('resvideo') and res.get('resvideo').strip():
        video_id = extract_youtube_video_id(res['resvideo'])
    elif res.get('resvideobubble') and res.get('resvideobubble').strip():
        video_id = extract_youtube_video_id(res['resvideobubble'])
    elif domain_data.get('wr_video') and str(domain_data.get('wr_video', '')).strip():
        video_id = extract_youtube_video_id(domain_data['wr_video'])
    
    if video_id:
        title_attr = clean_title(seo_filter_text_custom(res.get("restitle", "")))
        wpage += f'<div class="vid-container dddd"><iframe title="{title_attr}" style="max-width:100%;margin-bottom:20px;" src="//www.youtube.com/embed/{video_id}" width="900" height="480"></iframe></div>'
        wpage += f'<div class="{css_prefix}-spacer"></div>\n'
    
    # Handle snapshot/image insertion (PHP lines 327-463)
    if domain_data.get('showsnapshot') == 1 and check_image_src_gpt(html.unescape(seo_filter_text_custom(res.get('resfulltext', '')))) == 1:
        moneynofollow = ''
        if artpageid != 0 and (artdomainid == 87252 or True):
            moneynofollow = ''
        
        if not res.get('linkouturl'):
            im = f'<a{moneynofollow} style="display: inline;" href="{resurl}">'
        else:
            im = f'<a{moneynofollow} href="{res["linkouturl"].replace("&amp;", "&")}">'
        
        im += f'<img src="//imagehosting.space/feed/pageimage.php?domain={domain_data["domain_name"]}" class="align-left" style="width:320px !important;height:260px;" alt="{clean_title(seo_filter_text_custom(res.get("restitle", "")))}">'
        im += '</a>'
        
        # Insert image after first heading (PHP line 337)
        resfulltext = html.unescape(seo_filter_text_custom(res.get('resfulltext', '')))
        resfulltext = insert_after_first_heading(resfulltext, im)
        res['resfulltext'] = html.escape(resfulltext)
    
    # Build text content with keyword linking (PHP lines 466-557)
    textkeywd = clean_title(seo_filter_text_custom(res.get('restitle', '')))
    
    if len(res.get('resfulltext', '').strip()) > 50 and domain_data.get('writerlock') != 1:
        linkedtexted = html.unescape(seo_filter_text_custom(res.get('resfulltext', '')))
        
        # Determine URL for linking (PHP lines 472-485)
        if offpageid != 0:
            # Build offselfurl (simplified - would need full off_category logic)
            theurl = linkdomain
        elif artpageid != 0:
            # Build artselfurl (simplified - would need full art_category logic)
            theurl = linkdomain
        elif len(res.get('linkouturl', '').strip()) <= 0:
            theurl = resurl
        else:
            theurl = res.get('linkouturl', '').replace('&amp;', '&')
        
        # Collect supporting keywords for content linking
        supporting_keywords = []
        supporting_keyword_urls = []
        
        if offdomainid != 0:
            # Support keywords for offsite (PHP lines 488-504)
            support_sql = """
                SELECT id, restitle FROM bwp_bubblefeedsupport 
                WHERE bubblefeedid = %s AND domainid = %s AND deleted != 1 AND LENGTH(resfulltext) > 300
            """
            thesupports = db.fetch_all(support_sql, (res.get('bubblefeedid', res.get('id', '')), offdomainid))
            for thesupport in thesupports:
                # Build offsupportselfurl (simplified)
                offsupportselfurl = linkdomain + '/' + seo_slug(seo_filter_text_custom(thesupport['restitle'])) + '-' + str(thesupport['id']) + '/'
                # Collect for content linking (max 2)
                if len(supporting_keywords) < 2:
                    supporting_keywords.append(thesupport['restitle'])
                    supporting_keyword_urls.append(offsupportselfurl)
        elif support == 0 and is_seom(domain_data.get('servicetype')):
            # Support keywords for SEOM (PHP lines 505-512)
            support_sql = """
                SELECT id, restitle FROM bwp_bubblefeedsupport 
                WHERE bubblefeedid = %s AND domainid = %s AND deleted != 1 AND LENGTH(resfulltext) > 300
            """
            thesupports = db.fetch_all(support_sql, (bubbleid, domainid))
            for thesupport in thesupports:
                thesupporturl = linkdomain + '/' + seo_slug(seo_filter_text_custom(thesupport['restitle'])) + '-' + str(thesupport['id']) + '/'
                # Collect for content linking (max 2)
                if len(supporting_keywords) < 2:
                    supporting_keywords.append(thesupport['restitle'])
                    supporting_keyword_urls.append(thesupporturl)
        elif support != 0 and (is_seom(domain_data.get('servicetype')) or is_bron(domain_data.get('servicetype'))):
            # Support keywords for support page (PHP lines 515-532)
            mainkw_sql = "SELECT restitle, linkouturl, id FROM bwp_bubblefeed WHERE id = %s"
            mainkw = db.fetch_row(mainkw_sql, (res.get('bubblefeedid', res.get('id', '')),))
            if mainkw:
                if len(mainkw.get('linkouturl', '')) > 5:
                    mainkwurl = mainkw['linkouturl']
                else:
                    mainkwurl = linkdomain + '/' + seo_slug(seo_filter_text_custom(mainkw['restitle'])) + '-' + str(mainkw['id']) + '/'
                # Collect for content linking (max 2)
                if len(supporting_keywords) < 2:
                    supporting_keywords.append(mainkw['restitle'])
                    supporting_keyword_urls.append(mainkwurl.replace('&amp;', '&'))
                
                # Get other support keyword
                osupkw_sql = """
                    SELECT restitle, id FROM bwp_bubblefeedsupport 
                    WHERE bubblefeedid = %s AND restitle != %s
                """
                osupkw = db.fetch_row(osupkw_sql, (res.get('bubblefeedid', res.get('id', '')), res.get('restitle', '')))
                if osupkw:
                    osupkwurl = linkdomain + '/' + seo_slug(seo_filter_text_custom(osupkw['restitle'])) + '-' + str(osupkw['id']) + '/'
                    # Collect for content linking (max 2)
                    if len(supporting_keywords) < 2:
                        supporting_keywords.append(osupkw['restitle'])
                        supporting_keyword_urls.append(osupkwurl.replace('&amp;', '&'))
        
        # Link keywords in content: the keyword matching the current page → homepage, others → their content pages
        # link_keywords_in_content now handles both in-content linking and appending unfound keywords
        current_page_keyword = res.get('restitle', '')
        
        # Determine the actual main keyword (not necessarily the current page)
        # If we're on a supporting keyword page (support == 1), get main keyword from bubblefeedid
        # Otherwise, the current page is the main keyword
        if support == 1 and res.get('bubblefeedid'):
            # We're on a supporting keyword page, get the main keyword
            mainkw_sql = "SELECT restitle, id FROM bwp_bubblefeed WHERE id = %s"
            mainkw = db.fetch_row(mainkw_sql, (res.get('bubblefeedid'),))
            if mainkw:
                actual_main_keyword = mainkw['restitle']
                main_keyword_id = mainkw['id']
            else:
                actual_main_keyword = res.get('restitle', '')
                main_keyword_id = bubbleid
        else:
            # We're on the main keyword page
            actual_main_keyword = res.get('restitle', '')
            main_keyword_id = bubbleid
        
        # Check if current page keyword matches a supporting keyword
        current_is_supporting = False
        supporting_keyword_index = -1
        for i, supp_kw in enumerate(supporting_keywords):
            if supp_kw and supp_kw.lower() == current_page_keyword.lower():
                current_is_supporting = True
                supporting_keyword_index = i
                break
        
        # Determine URLs: keyword matching current page → homepage, others → their content pages
        if current_is_supporting:
            # Current page is a supporting keyword: that supporting keyword → homepage
            supporting_keyword_urls[supporting_keyword_index] = linkdomain + '/'
            # Main keyword → main keyword page
            main_keyword_url = linkdomain + '/' + seo_slug(seo_filter_text_custom(actual_main_keyword)) + '-' + str(main_keyword_id) + '/'
        elif current_page_keyword.lower() == actual_main_keyword.lower():
            # Current page is the main keyword: main keyword → homepage
            main_keyword_url = linkdomain + '/'  # Homepage
            # Supporting keywords → their respective pages (already set correctly)
        else:
            # Fallback: main keyword → homepage
            main_keyword_url = linkdomain + '/'
        
        linkedtexted = link_keywords_in_content(
            content=linkedtexted,
            main_keyword=actual_main_keyword,
            main_keyword_url=main_keyword_url,
            supporting_keywords=supporting_keywords,
            supporting_keyword_urls=supporting_keyword_urls,
            append_unfound=True  # Append unfound keywords for resfulltext
        )
        
        # Wrap content in wr-fulltext div to allow text wrapping around images
        wpage += '<div class="wr-fulltext">\n'
        wpage += linkedtexted
        wpage += '</div>\n'
    elif len(res.get('resshorttext', '').strip()) > 50:
        # Use shorttext if fulltext not available (PHP lines 535-557)
        linkedtexted = html.unescape(res.get('resshorttext', ''))
        
        # Determine URL for linking
        if offpageid != 0:
            theurl = linkdomain
        elif artpageid != 0:
            if domain_data.get('writerlock') == 1:
                linkedtexted = ''
            theurl = linkdomain
        elif len(res.get('linkouturl', '').strip()) < 5:
            theurl = resurl
        else:
            theurl = res.get('linkouturl', '').replace('&amp;', '&')
        
        # Get supporting keywords for content linking
        supporting_keywords = []
        supporting_keyword_urls = []
        if support == 0 and is_seom(domain_data.get('servicetype')):
            # Support keywords for SEOM
            support_sql = """
                SELECT id, restitle FROM bwp_bubblefeedsupport 
                WHERE bubblefeedid = %s AND domainid = %s AND deleted != 1 AND LENGTH(resfulltext) > 300
            """
            thesupports = db.fetch_all(support_sql, (bubbleid, domainid))
            for thesupport in thesupports[:2]:  # Limit to 2
                thesupporturl = linkdomain + '/' + seo_slug(seo_filter_text_custom(thesupport['restitle'])) + '-' + str(thesupport['id']) + '/'
                supporting_keywords.append(thesupport['restitle'])
                supporting_keyword_urls.append(thesupporturl)
        
        # Link keywords in content: the keyword matching the current page → homepage, others → their content pages
        # link_keywords_in_content now handles both in-content linking and appending unfound keywords
        current_page_keyword = res.get('restitle', '')
        
        # For resshorttext, we're always on the main keyword page (not supporting)
        actual_main_keyword = res.get('restitle', '')
        main_keyword_id = bubbleid
        
        # Check if current page keyword matches a supporting keyword
        current_is_supporting = False
        supporting_keyword_index = -1
        for i, supp_kw in enumerate(supporting_keywords):
            if supp_kw and supp_kw.lower() == current_page_keyword.lower():
                current_is_supporting = True
                supporting_keyword_index = i
                break
        
        # Determine URLs: keyword matching current page → homepage, others → their content pages
        if current_is_supporting:
            # Current page is a supporting keyword: that supporting keyword → homepage
            supporting_keyword_urls[supporting_keyword_index] = linkdomain + '/'
            # Main keyword → main keyword page
            main_keyword_url = linkdomain + '/' + seo_slug(seo_filter_text_custom(actual_main_keyword)) + '-' + str(main_keyword_id) + '/'
        else:
            # Current page is the main keyword: main keyword → homepage
            main_keyword_url = linkdomain + '/'  # Homepage
            # Supporting keywords → their respective pages (already set correctly)
        
        linkedtexted = link_keywords_in_content(
            content=linkedtexted,
            main_keyword=actual_main_keyword,
            main_keyword_url=main_keyword_url,
            supporting_keywords=supporting_keywords,
            supporting_keyword_urls=supporting_keyword_urls,
            append_unfound=False  # Don't append unfound keywords for resshorttext
        )
        
        # Wrap content in wr-fulltext div to allow text wrapping around images
        wpage += '<div class="wr-fulltext">\n'
        wpage += linkedtexted
        wpage += '</div>\n'
    
    # Related posts - drip content (bubbafeed) (PHP lines 879-917)
    if res.get('id'):
        bubba_sql = """
            SELECT * FROM bwp_bubbafeed
            WHERE bubblefeedid = %s AND active = '1' 
            AND char_length(resfulltext) > 300 AND deleted != '1'
            ORDER BY createdDate DESC
        """
        resbubba = db.fetch_all(bubba_sql, (res['id'],))
        
        if resbubba:
            wpage += f'<div class="{css_prefix}-spacer"></div>\n'
            wpage += f'<div class="{css_prefix}-container-wr-full">\n'
            
            for bubba in resbubba:
                title = clean_title(seo_filter_text_custom(bubba.get('bubbatitle', '')))
                titlelink = title.lower().replace(' ', '-')
                titlelink = to_ascii(html.unescape(titlelink))
                resurl_bubba = linkdomain + '/' + seo_text_custom(titlelink) + '-' + str(bubba['id']) + 'dc'
                
                wpage += f'<div class="{css_prefix}-containerwr moinfomation">\n'
                wpage += f'<h2 class="h2"><a target="_top" title="{title}" href="{resurl_bubba}">{title}</a></h2>\n'
                
                bubbatext = strip_html(html.unescape(seo_filter_text_custom(bubba.get('resfulltext', ''))))
                bubbatext = trim_to_first_n_words(bubbatext, 75)
                bubbatext = bubbatext.replace('//gallery.imagehosting.space/gallery/', '//gallery.imagehosting.space/thumbs/')
                wpage += bubbatext
                wpage += '</div>\n'
                wpage += f'<div class="{css_prefix}-spacer"></div>\n'
            
            wpage += '</div>\n'
    
    # Related posts - related articles (PHP lines 918-1020)
    if res.get('restitle') and res.get('restitle') == res.get('category'):
        # Get related articles from same category (PHP lines 918-929)
        related_sql = """
            SELECT b.*, c.category
            FROM bwp_bubblefeed b
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid
            WHERE b.categoryid = %s AND b.restitle != %s
            AND b.active = '1' AND b.deleted != '1' AND c.deleted != 1
            ORDER BY createdDate DESC
        """
        resrelated = db.fetch_all(related_sql, (res.get('categoryid', ''), res.get('restitle', '')))
        
        if resrelated:
            wpage += '<h2 class="h1">Related Posts</h2>\n'
            wpage += f'<div class="{css_prefix}-spacer"></div>\n'
            wpage += f'<div class="{css_prefix}-container-wr-full">\n'
            
            for rel in resrelated:
                resfulltext_rel = html.unescape(seo_filter_text_custom(rel.get('resfulltext', '')))
                if len(resfulltext_rel) > 50:
                    wpage += f'<div class="{css_prefix}-containerwr">\n'
                    titledecoded = seo_filter_text_custom(rel.get('restitle', ''))
                    wpage += f'<h2 class="h2"><a target="_top" title="{titledecoded}" href="/">{titledecoded}</a></h2>\n'
                    wpage += resfulltext_rel
                    wpage += f'<div class="{css_prefix}-spacer"></div>\n'
                    
                    # Get bubbafeed for related article (PHP lines 977-1016)
                    bubba_rel_sql = """
                        SELECT * FROM bwp_bubbafeed
                        WHERE bubblefeedid = %s AND active = '1' 
                        AND char_length(resfulltext) > 300 AND deleted != '1'
                        ORDER BY createdDate DESC
                    """
                    resbubba_rel = db.fetch_all(bubba_rel_sql, (rel['id'],))
                    
                    if resbubba_rel and domain_data.get('servicetype') != 10:
                        for bubba_rel in resbubba_rel:
                            title_rel = clean_title(seo_filter_text_custom(bubba_rel.get('bubbatitle', '')))
                            titlelink_rel = title_rel.lower().replace(' ', '-')
                            titlelink_rel = to_ascii(html.unescape(titlelink_rel))
                            resurl_bubba_rel = linkdomain + '/' + seo_text_custom(titlelink_rel) + '-' + str(bubba_rel['id']) + 'dc'
                            
                            wpage += '<div class="seo-automation-containerwr moinfomation">\n'
                            wpage += f'<h2 class="h2"><a target="_top" title="{title_rel}" href="{resurl_bubba_rel}">{title_rel}</a></h2>\n'
                            
                            bubbatext_rel = strip_html(html.unescape(seo_filter_text_custom(bubba_rel.get('resfulltext', ''))))
                            bubbatext_rel = trim_to_first_n_words(bubbatext_rel, 75)
                            bubbatext_rel = bubbatext_rel.replace('//gallery.imagehosting.space/gallery/', '//gallery.imagehosting.space/thumbs/')
                            wpage += bubbatext_rel
                            wpage += '</div>\n'
                            wpage += '<div class="seo-automation-spacer"></div>\n'
                    
                    wpage += '</div>\n'
            
            wpage += '</div>\n'
    
    # Google Maps section (PHP lines 1022-1487)
    ssmap = 0
    if domain_data.get('showmap'):
        if domain_data.get('wr_address') or res.get('resaddress'):
            map_val = 0
            addres = res.get('resaddress') or domain_data.get('wr_address', '')
            phon = res.get('resphone') or domain_data.get('wr_phone', '')
            
            stadd = ''
            cty = ''
            state = ''
            zip_code = ''
            mapurl = ''
            
            if addres:
                address = seo_filter_text_custom(addres)
                address = html.unescape(address)
                addressarray = address.split(',')
                if len(addressarray) == 3:
                    stzipstr = addressarray[2]
                    stziparray = stzipstr.strip().split(' ')
                    if len(stziparray) == 2:
                        stadd = addressarray[0].strip()
                        cty = addressarray[1].strip()
                        state = stziparray[0].strip()
                        zip_code = stziparray[1].strip()
                        map_val = 1
                    elif len(stziparray) == 3:
                        stadd = addressarray[0].strip()
                        cty = addressarray[1].strip()
                        state = stziparray[0].strip()
                        zip_code = stziparray[1].strip()
                        zip_code += ' ' + stziparray[2].strip()
                        map_val = 1
            
            if map_val == 1:
                wpage += f'<div class="{css_prefix}-spacer"></div>\n'
                wpage += '<div class="google-map">\n'
                mpadd = ''
                
                if res.get('resname'):
                    wpage += '<div itemscope itemtype="http://schema.org/LocalBusiness">\n'
                    wpage += f'<span itemprop="name" style=""><strong>{seo_filter_text_customapi(res["resname"])}</strong></span> '
                    if res.get('resgooglemaps'):
                        wpage += f'<a href="{res["resgooglemaps"]}" title="Find us on Google" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="https://seopanel.imagehosting.space/images/maps15_bnuw3a_32dp.ico" border="0" width="16" alt="Best Seo Wordpress Plugin"></a>'
                    mpadd = res['resname']
                    ssmap = 1
                elif domain_data.get('wr_name'):
                    wpage += '<div itemscope itemtype="http://schema.org/LocalBusiness">\n'
                    wpage += f'<span itemprop="name" style=""><strong>{seo_filter_text_customapi(domain_data["wr_name"])}</strong></span> '
                    if res.get('resgooglemaps'):
                        wpage += f'<a href="{res["resgooglemaps"]}" title="Find us on Google" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="https://seopanel.imagehosting.space/images/maps15_bnuw3a_32dp.ico" border="0" width="16" alt="Best Seo Wordpress Plugin"></a>'
                    mpadd = domain_data['wr_name']
                    ssmap = 1
                
                if phon:
                    wpage += f'<div style="" itemprop="telephone">{phon}</div>\n'
                
                cntry = domain_data.get('domain_country', '')
                wpage += '<div itemprop="address" itemscope itemtype="http://schema.org/PostalAddress">\n'
                wpage += f'<div style="" itemprop="streetAddress">{stadd}</div>\n'
                wpage += f'<span style="" itemprop="addressLocality">{cty}</span>\n'
                wpage += f'<span style="" itemprop="addressRegion">{state}</span>\n'
                wpage += f'<span style="" itemprop="postalCode">{zip_code}</span>\n'
                wpage += f'<span style="display:none !important;" itemprop="addressCountry">{cntry}</span>\n'
                
                imagesrc = '//imagehosting.space/feed/pageimage.php?domain=' + domain_data['domain_name']
                wpage += f'<meta itemprop="image" content="{imagesrc}"></meta>\n'
                wpage += '</div>\n'
                
                # Build map URL
                if mpadd:
                    mapurl = f'https://www.google.com/maps/embed/v1/place?key=AIzaSyDET-f-9dCENEEt8nU2MLOXluoEtrq2k5o&q={quote(mpadd)}+{quote(addres.replace(",", ""))}'
                else:
                    mapurl = f'https://www.google.com/maps/embed/v1/place?key=AIzaSyDET-f-9dCENEEt8nU2MLOXluoEtrq2k5o&q={quote(addres.replace(",", ""))}'
                
                wpage += f'<iframe title="{mpadd}" width="280" height="160" style="border:0;overflow:hidden;" src="{mapurl}"></iframe>\n'
                
                if mpadd:
                    wpage += f'<br /><a href="https://maps.google.com/maps?q={quote(mpadd)}+{quote(addres.replace(",", ""))}" style="color:#0000FF;text-align:left">View Larger Map</a>\n'
                else:
                    wpage += f'<br /><a href="https://maps.google.com/maps?q={quote(addres.replace(",", ""))}" style="color:#0000FF;text-align:left">View Larger Map</a>\n'
                
                # Reviews schema (PHP lines 1137-1150)
                if domain_settings.get('reviewsch') == 1:
                    created_date = domain_data.get('createdDate', '')
                    if created_date:
                        if isinstance(created_date, str):
                            try:
                                past = datetime.strptime(created_date, '%Y-%m-%d %H:%M:%S')
                            except:
                                past = datetime.now() - timedelta(days=365)
                        else:
                            past = created_date
                    else:
                        past = datetime.now() - timedelta(days=365)
                    
                    now = datetime.now()
                    days_old = (now - past).days
                    rating = round(random.uniform(4.7, 4.9), 1)
                    
                    wpage += f'''
<div itemscope itemtype="https://schema.org/Product">
    <span class="product_name" itemprop="name">{mpadd}</span>&nbsp; &nbsp;<img src="/wp-content/themes/woodmart-child/4.9stars.png" style="max-width:100px"/>
    <div itemprop="aggregateRating" itemscope itemtype="https://schema.org/AggregateRating">
        Rated <span itemprop="ratingValue">{rating}</span>/5 based on <span itemprop="reviewCount">{days_old}</span> customer reviews
    </div>
</div>
'''
                
                wpage += '</div>\n'
    
    # Social media icons (PHP lines 1493-1508)
    if (len(res.get('resgoogle', '')) > 10 or len(res.get('resfb', '')) > 10 or 
        len(res.get('resx', '')) > 10 or len(res.get('reslinkedin', '')) > 10 or
        len(res.get('resinstagram', '')) > 10 or len(res.get('restiktok', '')) > 10 or
        len(res.get('respinterest', '')) > 10):
        if len(res.get('resgoogle', '')) > 10:
            wpage += f'<a href="{res["resgoogle"]}" title="{res.get("restitle", "")} - Find us on Google" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="//seopanel.imagehosting.space/images/maps15_bnuw3a_32dp.ico" border="0" width="16" alt="{res.get("restitle", "")}"></a>'
        if len(res.get('resfb', '')) > 10:
            wpage += f'<a href="{res["resfb"]}" title="{res.get("restitle", "")} - Follow us on Facebook" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="//imagehosting.space/images/fbfavicon.ico" width="16" alt="{res.get("restitle", "")}"></a>'
        if len(res.get('resx', '')) > 10:
            wpage += f'<a href="{res["resx"]}" title="{res.get("restitle", "")} - Follow us on X" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="//www.x.com/favicon.ico" width="16" alt="{res.get("restitle", "")}"></a>'
        if len(res.get('reslinkedin', '')) > 10:
            wpage += f'<a href="{res["reslinkedin"]}" title="{res.get("restitle", "")} - Follow us on LinkedIn" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="//imagehosting.space/images/linkfavicon.ico" border="0" width="16" alt="{res.get("restitle", "")}"></a>'
        if len(res.get('resinstagram', '')) > 10:
            wpage += f'<a href="{res["resinstagram"]}" title="{res.get("restitle", "")} - Follow us on Instagram" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="//www.instagram.com/favicon.ico" border="0" width="16" alt="{res.get("restitle", "")}"></a>'
        if len(res.get('restiktok', '')) > 10:
            wpage += f'<a href="{res["restiktok"]}" title="{res.get("restitle", "")} - Follow us on TikTok" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="//www.tiktok.com/favicon.ico" border="0" width="16" alt="{res.get("restitle", "")}"></a>'
        if len(res.get('respinterest', '')) > 10:
            wpage += f'<a href="{res["respinterest"]}" title="{res.get("restitle", "")} - Follow us on Penterest" target="_blank"><img style="padding:0px;max-width:16px;height:auto;" src="//www.pinterest.com/favicon.ico" border="0" width="16" alt="{res.get("restitle", "")}"></a>'
    
    # Add ArticleLinks (PHP line 1560: echocr(ArticleLinks($pageid)))
    # Only add ArticleLinks for non-WordPress plugin calls (PHP plugin calls)
    if domain_data.get('wp_plugin') != 1:
        # Get domain_category for ArticleLinks (it's the same as domain_data in this context)
        domain_category = domain_data
        article_links_html = build_article_links(
            pageid=bubbleid or 0,
            domainid=domainid,
            domain_data=domain_data,
            domain_settings=domain_settings,
            domain_category=domain_category
        )
        wpage += article_links_html
    
    # Add premiumstyles.css and closing styles (matching build_bcpage_wp)
    wpage += f'<div class="{css_prefix}-spacer"></div>\n'
    wpage += f'<div class="{css_prefix}-tag-container" style="border-bottom:1px solid black; border-top:1px solid black;"></div>\n'
    wpage += '<link rel="stylesheet" id="SEO_Automation_premium_0_X-css" href="https://public.imagehosting.space/external_files/premiumstyles.css" type="text/css" media="all" />\n'
    wpage += '<div class="seo-automation-spacer"></div>\n'
    
    # #region agent log
    div_counts_before_close = _count_divs(wpage)
    _debug_log("content.py:build_page_wp", "Before closing main div", {"wpage_length": len(wpage), "div_counts": div_counts_before_close}, "A")
    # #endregion
    
    wpage += '</div>\n'
    wpage += '''<style>
.ngodkrbsitr-spacer{clear:both;}
.citation_map_container iframe {
	width:130px !important;
}
.vid-container iframe {
	width:100% !important;
}
</style>
'''
    
    # #region agent log
    div_counts_final = _count_divs(wpage)
    _debug_log("content.py:build_page_wp", "Function exit", {"wpage_length": len(wpage), "div_counts": div_counts_final}, "A")
    # #endregion
    
    return wpage


def build_bcpage_wp(
    bubbleid: int,
    domainid: int,
    debug: bool,
    agent: str,
    domain_data: Dict[str, Any],
    domain_settings: Dict[str, Any],
    artpageid: int = 0,
    artdomainid: int = 0
) -> str:
    """
    Build Business Collective page HTML (Action=2).
    Replicates seo_automation_build_bcpage from businesscollective-wp.php
    """
    if not bubbleid or not domainid:
        return ""
    
    import html
    import re
    from urllib.parse import quote
    
    # Get bubblefeed data
    sql = """
        SELECT b.id, b.restitle, b.resfulltext, b.resshorttext, b.resfeedtext, b.linkouturl,
               IFNULL(c.id, '') AS categoryid, IFNULL(c.category, '') AS category
        FROM bwp_bubblefeed b
        LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != 1
        WHERE b.domainid = %s AND b.deleted != 1 AND b.id = %s
    """
    res = db.fetch_row(sql, (domainid, bubbleid))
    
    if not res:
        return ""
    
    # Build domain link
    if domain_settings.get('usedurl') == 1 and domain_data.get('domain_url'):
        dl = domain_data['domain_url'].rstrip('/')
    else:
        if domain_data.get('ishttps') == 1:
            dl = 'https://'
        else:
            dl = 'http://'
        if domain_data.get('usewww') == 1:
            dl += 'www.' + domain_data['domain_name']
        else:
            dl += domain_data['domain_name']
    
    # Build resurl
    # For Action=2 (feed pages), WordPress plugins should use /slug-idbc/ format
    if len(res.get('linkouturl', '')) > 5:
        resurl = res['linkouturl'].strip()
    else:
        # Initial build - will be overridden below for WordPress plugins with proper format
        resurl = dl + '/' + seo_slug(seo_filter_text_custom(res['restitle'])) + '-' + str(res['id']) + '/'
    
    # Get CSS class prefix based on wp_plugin
    css_prefix = get_css_class_prefix(domain_data.get('wp_plugin', 0))
    
    # Start building page (PHP lines 239-240)
    bcpage = f'<div class="{css_prefix}-main-table"><div class="{css_prefix}-spacer"></div>\n'
    bcpage += f'<div class="{css_prefix}-top-container">\n'
    
    # Build resurl for main keyword link (PHP lines 125-135)
    # PHP: if ($domain['status'] == 2 || $domain['status'] == 10)
    domain_status = domain_data.get('status')
    domain_status_str = str(domain_status) if domain_status is not None else ''
    script_version_num = get_script_version_num(domain_data.get('script_version'))
    
    if domain_status_str in ['2', '10']:
        # For WordPress plugins, always use WordPress URL structure
        # resurl is used for H1 link which should point to Action=1 (main page) - /slug-id/ (no bc suffix)
        # Action=2 (feed pages) URLs with 'bc' suffix are built separately when linking TO feed pages
        if domain_data.get('wp_plugin') == 1:
            slug_text = seo_text_custom(res.get('restitle', ''))
            slug_text = html.unescape(slug_text)
            slug_text = to_ascii(slug_text)
            slug_text = slug_text.lower()
            slug_text = slug_text.replace(' ', '-')
            # H1 link points to main page (Action=1) - no 'bc' suffix
            resurl = dl + '/' + slug_text + '-' + str(res.get('id', '')) + '/'
        else:
            # PHP: if($rd == 1 && $domain_category['script_version'] >= 3 && $domain_category['wp_plugin'] != 1 && $domain_category['iswin'] != 1 && $domain_category['usepurl'] != 0)
            # For now, use CodeURL equivalent (simplified)
            resurl = code_url(domainid, domain_data, domain_settings) + "?Action=1&amp;k=" + seo_slug(seo_filter_text_custom(res.get('restitle', ''))) + '&amp;PageID=' + str(res.get('id', ''))
    else:
        resurl = dl
    
    # PHP line 241: H1 with " - Resources" suffix
    bcpage += f'<h1 class="h1"><a href="{resurl}" style="">{clean_title(seo_filter_text_custom(res.get("restitle", "")))} - Resources</a></h1>\n'
    
    # PHP lines 242-257: Supporting keywords as H2 links for SEOM/BRON
    servicetype = domain_data.get('servicetype')
    isSEOM_val = is_seom(servicetype)
    isBRON_val = is_bron(servicetype)
    
    # Initialize supportkwords for use in keyword linking later
    supportkwords = []
    if isSEOM_val or isBRON_val:
        support_sql = """
            SELECT restitle, id FROM bwp_bubblefeedsupport 
            WHERE domainid = %s AND bubblefeedid = %s AND deleted != 1 AND LENGTH(resfulltext) > 300 
            ORDER BY LENGTH(restitle) DESC
        """
        supportkwords = db.fetch_all(support_sql, (domainid, res['id']))
        if supportkwords:
            for support in supportkwords:
                # PHP line 249-252: Build resurl1 for support keyword
                # For WordPress plugins, always use WordPress URL structure (/slug-id/)
                if domain_data.get('wp_plugin') == 1:
                    # WordPress URL structure: /slug-id/
                    slug_text = seo_text_custom(support['restitle'])
                    slug_text = html.unescape(slug_text)
                    slug_text = to_ascii(slug_text)
                    slug_text = slug_text.lower()
                    slug_text = slug_text.replace(' ', '-')
                    resurl1 = dl + '/' + slug_text + '-' + str(support['id']) + '/'
                elif script_version_num >= 3 and domain_data.get('wp_plugin') != 1 and domain_data.get('iswin') != 1 and domain_data.get('usepurl') != 0:
                    # Use vardomain format
                    cdomain = domain_data['domain_name'].split('.')
                    vardomain = cdomain[0] if cdomain else ''
                    slug_text = seo_text_custom(support['restitle'])
                    slug_text = html.unescape(slug_text)
                    slug_text = to_ascii(slug_text)
                    slug_text = slug_text.lower()
                    slug_text = slug_text.replace(' ', '-')
                    resurl1 = dl + '/' + vardomain + '/' + slug_text + '/' + str(support['id']) + '/'
                else:
                    # Use CodeURL
                    resurl1 = code_url(domainid, domain_data, domain_settings) + "?Action=1&amp;k=" + seo_slug(seo_filter_text_custom(support['restitle'])) + '&amp;PageID=' + str(support['id'])
                
                # PHP line 254: H2 link for support keyword
                bcpage += f'<h2 class="h2"><a href="{resurl1}" style="">{custom_ucfirst_words(clean_title(seo_filter_text_custom(support["restitle"])))}</a></h2>\n'
    
    # PHP lines 258-261: Social media icons (if showgoogleplusone)
    # Note: showgoogleplusone is not in domain_data, so we'll skip for now
    
    # PHP line 262: Spacer
    bcpage += f'<div class="{css_prefix}-spacer"></div>\n'
    
    # PHP lines 264-283: Video or image
    if not domain_data.get('wr_video'):
        # PHP line 265-267: Image
        bcpage += f'<a href="{resurl}" target="_blank"><img src="//imagehosting.space/feed/pageimage.php?domain={domain_data["domain_name"]}" alt="{clean_title(seo_filter_text_custom(res.get("restitle", "")))}" style="width:160px  !important;height:130px;" class="align-left"></a>\n'
    else:
        # PHP lines 271-282: Video
        vid = domain_data['wr_video']
        vid = seo_filter_text_custom(vid)
        vid = vid.replace('https://www.', '')
        vid = vid.replace('http://www.', '')
        vid = vid.replace('http://', '')
        vid = vid.replace('//', '')
        vid = vid.replace('youtu.be/', '')
        vid = vid.replace('youtube.com/embed/', '')
        vid = vid.replace('youtube.com/watch?v=', '')
        vid = vid.replace('www.', '')
        # Remove &feature=... and similar parameters
        vid = re.sub(r'&.*feature.*', '', vid)
        if vid:
            bcpage += f'<div class="vid-outer"><div class="vid-container"><iframe style="max-width:100%;" src="//www.youtube.com/embed/{vid}" width="900" height="480"></iframe></div></div>\n'
    
    # Get resfeedtext or resshorttext (PHP lines 115-123)
    if res.get('resfeedtext') and res['resfeedtext'].strip():
        shorttext = res['resfeedtext']
        shorttext = shorttext.replace('Table of Contents', '').strip()
    elif res.get('resshorttext') and res['resshorttext'].strip():
        shorttext = res['resshorttext']
        shorttext = shorttext.replace('Table of Contents', '').strip()
    else:
        shorttext = ''
    
    # PHP line 285: Output shorttext
    if shorttext:
        shorttext = html.unescape(str(shorttext))
        shorttext = seo_filter_text_custom(shorttext)
        
        # Link keywords in content: main keyword → homepage, supporting keywords → their pages
        # Get supporting keywords (max 2) for content linking
        supporting_keywords = []
        supporting_keyword_urls = []
        if (isSEOM_val or isBRON_val) and supportkwords:
            for support in supportkwords[:2]:  # Limit to 2
                # Build URL for supporting keyword (same logic as above)
                if domain_data.get('wp_plugin') == 1:
                    slug_text = seo_text_custom(support['restitle'])
                    slug_text = html.unescape(slug_text)
                    slug_text = to_ascii(slug_text)
                    slug_text = slug_text.lower()
                    slug_text = slug_text.replace(' ', '-')
                    suppurl = dl + '/' + slug_text + '-' + str(support['id']) + '/'
                elif script_version_num >= 3 and domain_data.get('wp_plugin') != 1 and domain_data.get('iswin') != 1 and domain_data.get('usepurl') != 0:
                    # Use vardomain format
                    cdomain = domain_data['domain_name'].split('.')
                    vardomain = cdomain[0] if cdomain else ''
                    slug_text = seo_text_custom(support['restitle'])
                    slug_text = html.unescape(slug_text)
                    slug_text = to_ascii(slug_text)
                    slug_text = slug_text.lower()
                    slug_text = slug_text.replace(' ', '-')
                    suppurl = dl + '/' + vardomain + '/' + slug_text + '/' + str(support['id']) + '/'
                else:
                    # Use CodeURL
                    suppurl = code_url(domainid, domain_data, domain_settings) + "?Action=1&k=" + seo_slug(seo_filter_text_custom(support['restitle'])) + '&PageID=' + str(support['id'])
                supporting_keywords.append(support['restitle'])
                supporting_keyword_urls.append(suppurl)
        
        main_keyword = res.get('restitle', '')
        main_keyword_url = dl + '/'  # Homepage
        shorttext = link_keywords_in_content(
            content=shorttext,
            main_keyword=main_keyword,
            main_keyword_url=main_keyword_url,
            supporting_keywords=supporting_keywords,
            supporting_keyword_urls=supporting_keyword_urls,
            append_unfound=True  # Append unfound keywords for resfeedtext (similar to resfulltext)
        )
        
        bcpage += shorttext + '\n'
    
    # PHP line 286: Close ngodkrbsitr-top-container
    bcpage += '</div>\n'
    
    # PHP lines 289-292: Spacer and "Additional Resources" header
    bcpage += f'<div class="{css_prefix}-spacer"></div><div class="{css_prefix}-tag-container" style="border-bottom:0px solid black; border-top:0px solid black;height:10px;"></div>\n'
    bcpage += '<h3 style="text-align:left;font-size:18px;font-weight:bold;">Additional Resources:</h3>\n'
    
    # Additional Resources section (keyword links) - PHP lines 297-1337
    domain_status = domain_data.get('status')
    # Convert to string for comparison (handles both int and str from DB)
    domain_status_str = str(domain_status) if domain_status is not None else ''
    if domain_status_str in ['1', '2', '8', '10']:
        links_sql = """
            SELECT d.*, b.restitle, b.resshorttext, b.resfulltext, b.linkouturl, b.resname, b.resaddress, b.resphone, 
                   l.linkformat, l.deeplink, l.relevant, b.id AS bubblefeedid, b.title, b.categoryid,
                   s.servicetype AS servicename, s.price, d.servicetype,
                   bc.category AS bubblecat, bc.bubblefeedid AS bubblecatid,
                   c.category AS subcat,
                   mc.maincategories_name AS maincat,
                   d.showtagsonbusinesscollective, d.usewebsitereferencetitles
            FROM bwp_link_placement l
            LEFT JOIN bwp_domains d ON d.id = l.domainid
            LEFT JOIN bwp_services s ON d.servicetype = s.id
            LEFT JOIN bwp_bubblefeed b ON b.id = l.bubblefeedid
            LEFT JOIN bwp_bubblefeedcategory bc ON bc.id = b.categoryid
            LEFT JOIN bwp_domain_category c ON c.id = d.domain_category
            LEFT JOIN bwp_maincategories mc ON mc.maincategories_id = c.parent_catid
            WHERE l.showondomainid = %s
            AND l.showonpgid = %s
            AND l.deleted != 1
            AND l.linkformat = 'keyword'
            AND d.deleted != 1
            AND l.showondomainid NOT IN (SELECT domain_id FROM bwp_domains_disabled WHERE disabled_domain_id = d.id)
            AND d.domainip != %s
            ORDER BY l.relevant DESC
        """
        links = db.fetch_all(links_sql, (domainid, res['id'], domain_data.get('domainip', '')))
        
        if links:
            # Process each link (header already added above)
            for link in links:
                # Get link settings
                link_settings_sql = "SELECT * FROM bwp_domain_settings WHERE domainid = %s"
                link_settings = db.fetch_row(link_settings_sql, (link['id'],))
                if not link_settings:
                    db.execute("INSERT INTO bwp_domain_settings SET domainid = %s", (link['id'],))
                    link_settings = db.fetch_row(link_settings_sql, (link['id'],))
                
                # Build link domain URLs
                if link_settings.get('usedurl') == 1 and link.get('domain_url'):
                    linkdomain = link['domain_url'].rstrip('/')
                else:
                    if link.get('ishttps') == 1:
                        lprfx = 'https://'
                    else:
                        lprfx = 'http://'
                    if link.get('usewww') == 1:
                        linkdomain = lprfx + 'www.' + link['domain_name']
                    else:
                        linkdomain = lprfx + link['domain_name']
                
                linkdomainalone = linkdomain
                if link.get('ishttps') == 1:
                    lprfx = 'https://'
                else:
                    lprfx = 'http://'
                if link.get('usewww') == 1:
                    linkalone = lprfx + 'www.' + link['domain_name'] + '/'
                else:
                    linkalone = lprfx + link['domain_name'] + '/'
                
                if link.get('servicetype') == 370:
                    linkdomainalone = linkdomain + '/'
                
                bcdomain = link['domain_name'].split('.')
                bcvardomain = bcdomain[0] if bcdomain else ''
                
                bcpage += f'<div class="{css_prefix}-container">\n'
                # PHP line 894: Add spacer right after opening container (before H2)
                bcpage += f'<div class="{css_prefix}-spacer"></div>\n'
                
                # Determine link URL
                haslinks_sql = "SELECT count(id) FROM bwp_link_placement WHERE deleted != 1 AND showondomainid = %s AND showonpgid = %s"
                haslinks = db.fetch_one(haslinks_sql, (link['id'], link.get('bubblefeedid')))
                haslinks = haslinks or 0
                
                if haslinks >= 1:
                    haslinkspg = {'restitle': link.get('restitle'), 'showonpgid': link.get('bubblefeedid'), 'bubblefeedid': link.get('bubblefeedid')}
                else:
                    haslinkspg_sql = """
                        SELECT l.id, l.showonpgid, b.restitle, b.id AS bubblefeedid 
                        FROM bwp_link_placement l 
                        LEFT JOIN bwp_bubblefeed b ON b.id = l.showonpgid AND b.deleted != 1 
                        WHERE l.deleted != 1 AND b.restitle <> '' AND l.showondomainid = %s 
                        ORDER BY RAND() LIMIT 1
                    """
                    haslinkspg = db.fetch_row(haslinkspg_sql, (link['id'],))
                    if not haslinkspg:
                        haslinkspg = {}
                
                # Build link URL - match PHP logic exactly
                # PHP line 322-376: Complex conditional logic for link URL building
                haslinkspg_count = haslinks if haslinks else 0
                
                if haslinkspg_count > 0 and link.get('wp_plugin') != 1 and link.get('servicetype') == 356 and link.get('status') in ['2', '10']:
                    # PHP line 322-324: CodeURL for non-WP plugin with servicetype 356
                    # Simplified CodeURL - would need full implementation
                    linkurl = linkdomain + '/?Action=2&k=' + seo_slug(seo_filter_text_custom(haslinkspg.get('restitle', '')))
                elif haslinkspg_count > 0 and link.get('wp_plugin') == 1 and link.get('servicetype') == 356 and link.get('status') in ['2', '10']:
                    # PHP line 326-331: WP plugin with servicetype 356
                    if is_bron(link.get('servicetype')):
                        linkurl = linkdomain + '/' + str(haslinkspg.get('showonpgid', '')) + 'bc/'
                    else:
                        linkurl = linkdomain + '/' + seo_slug(seo_filter_text_custom(haslinkspg.get('restitle', ''))) + '-' + str(haslinkspg.get('showonpgid', '')) + 'bc/'
                elif len(link.get('linkouturl', '')) > 5 and link.get('status') in ['2', '10'] and (not is_seom(link.get('servicetype')) or is_bron(link.get('servicetype'))):
                    # PHP line 333: linkouturl if NOT SEOM OR if BRON
                    linkurl = link['linkouturl'].strip()
                elif link.get('skipfeedchecker') == 1:
                    # PHP line 337-340
                    linkurl = linkdomainalone
                elif not link.get('bubblecat') and link.get('wp_plugin') == 1 and (len(link.get('resfulltext') or '') >= 50 or len(link.get('resshorttext') or '') >= 50) and link.get('status') in ['2', '10']:
                    # PHP line 342-344: WP plugin without bubblecat
                    import html
                    slug_text = seo_text_custom(link.get('restitle', ''))
                    slug_text = html.unescape(slug_text)
                    slug_text = to_ascii(slug_text)
                    slug_text = slug_text.lower()
                    slug_text = slug_text.replace(' ', '-')
                    linkurl = linkdomain + '/' + slug_text + '-' + str(link.get('bubblefeedid', '')) + '/'
                elif link.get('wp_plugin') == 1 and (len(link.get('resfulltext') or '') >= 50 or len(link.get('resshorttext') or '') >= 50) and link.get('status') in ['2', '10']:
                    # PHP line 346-348: WP plugin with bubblecat
                    import html
                    slug_text = seo_text_custom(link.get('bubblecat', ''))
                    slug_text = html.unescape(slug_text)
                    slug_text = to_ascii(slug_text)
                    slug_text = slug_text.lower()
                    slug_text = slug_text.replace(' ', '-')
                    linkurl = linkdomain + '/' + slug_text + '-' + str(link.get('bubblecatid', '')) + '/'
                elif not link.get('bubblecat') and link.get('wp_plugin') != 1 and (len(link.get('resfulltext') or '') >= 50 or len(link.get('resshorttext') or '') >= 50) and link.get('status') in ['2', '10']:
                    # PHP line 350-355: Non-WP plugin without bubblecat
                    script_version_num = get_script_version_num(link.get('script_version'))
                    if script_version_num >= 3 and link.get('wp_plugin') != 1 and link.get('iswin') != 1 and link.get('usepurl') != 0:
                        linkurl = linkdomain + '/' + bcvardomain + '/' + seo_slug(seo_filter_text_custom(link.get('restitle', ''))) + '/' + str(link.get('bubblefeedid', '')) + '/'
                    else:
                        # CodeURL equivalent - simplified
                        linkurl = linkdomain + '/?Action=1&k=' + seo_slug(seo_filter_text_custom(link.get('restitle', ''))) + '&PageID=' + str(link.get('bubblefeedid', ''))
                elif link.get('wp_plugin') != 1 and link.get('status') in ['2', '10']:
                    # PHP line 357-362: Non-WP plugin with bubblecat
                    script_version_num = get_script_version_num(link.get('script_version'))
                    if script_version_num >= 3 and link.get('wp_plugin') != 1 and link.get('iswin') != 1 and link.get('usepurl') != 0:
                        linkurl = linkdomain + '/' + bcvardomain + '/' + seo_slug(seo_filter_text_custom(link.get('bubblecat', ''))) + '/' + str(link.get('bubblecatid', '')) + '/'
                    else:
                        # CodeURL equivalent - simplified
                        linkurl = linkdomain + '/?Action=1&k=' + seo_slug(seo_filter_text_custom(link.get('restitle', ''))) + '&PageID=' + str(link.get('bubblefeedid', ''))
                else:
                    # PHP line 372-375: Default fallback
                    linkurl = linkalone
                
                follow = ' rel="nofollow"' if link.get('forceinboundnofollow') == 1 else ''
                
                # PHP line 410-411: moneynofollow (empty string in this case)
                moneynofollow = ''
                
                # Build title
                if link.get('title'):
                    stitle = clean_title(seo_filter_text_custom(link['title']))
                else:
                    stitle = clean_title(seo_filter_text_custom(link.get('restitle', '')))
                
                bcpage += f'<h2 class="h2"><a{moneynofollow} title="{stitle}" href="{linkurl}" style="text-align:left;" target="_blank"{follow}>{stitle}</a></h2>\n'
                
                # Support links for SEOM/BRON services
                # PHP line 415: if((isSEOM($links[$i]['servicetype']) || isBRON($links[$i]['servicetype'])) && isset($links[$i]['bubblefeedid']))
                # isset() checks if key exists AND value is not NULL
                # Get servicetype from the linked domain (d.servicetype in the query)
                servicetype_val = link.get('servicetype')
                # Get bubblefeedid - this is b.id from bwp_bubblefeed (the id of the row whose restitle was just displayed)
                bubblefeedid_val = link.get('bubblefeedid')
                # PHP isset() returns true if key exists AND value is not NULL
                has_bubblefeedid = 'bubblefeedid' in link and bubblefeedid_val is not None
                
                # Debug: Log values to diagnose issue
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Support keywords check - restitle: {link.get('restitle')}, servicetype: {servicetype_val}, bubblefeedid: {bubblefeedid_val}, has_bubblefeedid: {has_bubblefeedid}")
                is_seom_result = is_seom(servicetype_val)
                is_bron_result = is_bron(servicetype_val)
                logger.info(f"is_seom({servicetype_val}): {is_seom_result}, is_bron({servicetype_val}): {is_bron_result}")
                
                # Check if the linked domain is SEOM or BRON
                if (is_seom_result or is_bron_result) and has_bubblefeedid:
                    # PHP line 417: Query doesn't filter by deleted != 1
                    support_sql = """
                        SELECT id, restitle FROM bwp_bubblefeedsupport 
                        WHERE bubblefeedid = %s AND LENGTH(resfulltext) > 300
                    """
                    # Query bwp_bubblefeedsupport where bubblefeedid matches the bwp_bubblefeed.id
                    supps = db.fetch_all(support_sql, (bubblefeedid_val,))
                    logger.info(f"Found {len(supps) if supps else 0} supporting keywords for bubblefeedid {bubblefeedid_val}")
                    if supps:
                        tsups = ''
                        for supp in supps:
                            suppurl = ''
                            # Convert status to int for comparison (PHP compares integers)
                            link_status = link.get('status')
                            if link_status is not None:
                                try:
                                    link_status = int(link_status)
                                except (ValueError, TypeError):
                                    link_status = None
                            
                            if link.get('wp_plugin') != 1 and link_status in [2, 10, 8]:
                                # Build suppurl for non-WP plugin
                                script_version_num = get_script_version_num(link.get('script_version'))
                                if script_version_num >= 3 and link.get('wp_plugin') != 1 and link.get('iswin') != 1 and link.get('usepurl') != 0:
                                    suppurl = linkdomain + '/' + bcvardomain + '/' + seo_slug(seo_filter_text_custom(supp['restitle'])) + '/' + str(supp['id']) + '/'
                                else:
                                    # PHP line 429: CodeURL($links[$i]['id']) . '?Action=1&amp;k=' ...
                                    # Use &amp; for HTML entities like PHP
                                    suppurl = linkdomain + '/?Action=1&amp;k=' + seo_slug(seo_filter_text_custom(supp['restitle'])) + '&amp;PageID=' + str(supp['id'])
                            elif link.get('wp_plugin') == 1 and link_status in [2, 10]:
                                # Use toAscii(html_entity_decode(seo_text_custom(...))) for WP plugin
                                import html
                                supp_slug_text = seo_text_custom(supp['restitle'])
                                supp_slug_text = html.unescape(supp_slug_text)
                                supp_slug_text = to_ascii(supp_slug_text)
                                supp_slug_text = supp_slug_text.lower()
                                supp_slug_text = supp_slug_text.replace(' ', '-')
                                suppurl = linkdomain + '/' + supp_slug_text + '-' + str(supp['id']) + '/'
                            
                            logger.info(f"Support keyword: {supp.get('restitle')}, wp_plugin: {link.get('wp_plugin')}, status: {link.get('status')}, suppurl: {suppurl}")
                            
                            if suppurl:
                                # PHP line 438: Use moneynofollow and custom_ucfirst_words(seo_text_custom(...)) for display
                                supp_title = custom_ucfirst_words(seo_text_custom(supp['restitle']))
                                tsups += '- <span style="font-size:12px;line-height:13px;"><strong> <a ' + moneynofollow + ' title="' + supp_title + '" href="' + suppurl + '" target="_blank"' + follow + '> ' + supp_title + ' </a> </strong></span> '
                        
                        # PHP line 443: ltrim($tsups, '-') - only remove leading dashes
                        tsups = tsups.lstrip('-')
                        logger.info(f"After lstrip, tsups length: {len(tsups)}, tsups: {tsups[:100] if tsups else 'EMPTY'}")
                        # PHP line 444-447: if($tsups != '') output it
                        if tsups:
                            logger.info(f"Outputting tsups to bcpage")
                            bcpage += tsups + '\n'
                        else:
                            logger.info(f"tsups is empty, not outputting")
                
                # Build image URL - match PHP logic exactly
                # PHP line 386-405: Complex conditional logic for image URL
                if link.get('skipfeedchecker') == 1 and link.get('linkskipfeedchecker') != 1:
                    # PHP line 386-388
                    imageurl = linkdomainalone
                elif haslinkspg_count > 0 and link.get('wp_plugin') != 1 and link.get('status') in ['2', '10', '8']:
                    # PHP line 390-395: Non-WP plugin with haslinkspg
                    script_version_num = get_script_version_num(link.get('script_version'))
                    if script_version_num >= 3 and link.get('wp_plugin') != 1 and link.get('iswin') != 1 and link.get('usepurl') != 0:
                        imageurl = linkdomain + '/' + bcvardomain + '/' + seo_slug(seo_filter_text_custom(haslinkspg.get('restitle', ''))) + '/' + str(haslinkspg.get('bubblefeedid', '')) + 'bc/'
                    else:
                        # CodeURL equivalent - simplified
                        imageurl = linkdomain + '/?Action=2&k=' + seo_slug(seo_filter_text_custom(haslinkspg.get('restitle', '')))
                elif (haslinkspg_count > 0 or is_bron(link.get('servicetype'))) and link.get('status') in ['2', '10', '8']:
                    # PHP line 397-402: haslinkspg > 0 OR isBRON
                    if is_bron(link.get('servicetype')):
                        imageurl = linkdomain + '/' + str(haslinkspg.get('showonpgid', '')) + 'bc/'
                    else:
                        import html
                        slug_text = seo_text_custom(haslinkspg.get('restitle', ''))
                        slug_text = html.unescape(slug_text)
                        slug_text = to_ascii(slug_text)
                        slug_text = slug_text.lower()
                        slug_text = slug_text.replace(' ', '-')
                        imageurl = linkdomain + '/' + slug_text + '-' + str(haslinkspg.get('showonpgid', '')) + 'bc/'
                else:
                    # PHP line 404-405: Default fallback
                    imageurl = linkalone
                
                # Build citation container if address/name exists
                preml = 0
                map_val = 0
                stadd = ''
                cty = ''
                state = ''
                zip_code = ''
                mapurl = ''
                address = ''
                
                if (link.get('wr_address') or link.get('resaddress')) and (link.get('wr_name') or link.get('resname')):
                    preml = 1
                    address = link.get('resaddress') or link.get('wr_address', '')
                    
                    if link_settings.get('gmbframe') and len(link_settings['gmbframe']) > 10:
                        mapurl = link_settings['gmbframe']
                        map_val = 1
                        # Parse address even when gmbframe exists
                        if address:
                            addressarray = address.split(',')
                            if len(addressarray) >= 3:
                                stzipstr = addressarray[2]
                                stziparray = stzipstr.strip().split(' ')
                                if len(stziparray) == 2:
                                    stadd = addressarray[0]
                                    cty = addressarray[1]
                                    state = stziparray[0]
                                    zip_code = stziparray[1]
                                elif len(stziparray) == 3:
                                    stadd = addressarray[0].strip()
                                    cty = addressarray[1].strip()
                                    state = stziparray[0].strip()
                                    zip_code = stziparray[1].strip()
                                    zip_code += ' ' + stziparray[2].strip()
                    elif address:
                        addressarray = address.split(',')
                        if len(addressarray) == 3:
                            stzipstr = addressarray[2]
                            stziparray = stzipstr.strip().split(' ')
                            if len(stziparray) == 2:
                                stadd = addressarray[0]
                                cty = addressarray[1]
                                state = stziparray[0]
                                zip_code = stziparray[1]
                                map_val = 1
                            elif len(stziparray) == 3:
                                stadd = addressarray[0].strip()
                                cty = addressarray[1].strip()
                                state = stziparray[0].strip()
                                zip_code = stziparray[1].strip()
                                zip_code += ' ' + stziparray[2].strip()
                                map_val = 1
                            
                            if map_val == 1:
                                wr_name = link.get('resname') or link.get('wr_name', '')
                                mapurl = f'https://www.google.com/maps/embed/v1/place?key=AIzaSyDET-f-9dCENEEt8nU2MLOXluoEtrq2k5o&q={quote(wr_name)}+{quote(address.replace(",", ""))}'
                
                # Citation container is ALWAYS created when preml == 1 (PHP line 531)
                if preml == 1:
                    bcpage += '<div class="bwp_citation_conatainer">\n'
                    bcpage += '<div itemscope itemtype="http://schema.org/LocalBusiness">\n'
                    bcpage += '<div class="citation_map_container">\n'
                    
                    if map_val == 1:
                        bcpage += f'<iframe width="130" height="110" style="width:130px;height:110px;border:0;overflow:hidden;" src="{mapurl}"></iframe>\n'
                        bcpage += f'<img itemprop="image" src="//imagehosting.space/feed/pageimage.php?domain={link["domain_name"]}" alt="{link["domain_name"]}" style="display:none !important;">\n'
                    else:
                        bcpage += f'<a href="{imageurl}" target="_blank"{follow}><img itemprop="image" src="//imagehosting.space/feed/pageimage.php?domain={link["domain_name"]}" alt="{link["domain_name"]}" style="width:130px !important;height:110px;"></a>\n'
                    
                    bcpage += '</div>\n'
                    
                    wr_name = link.get('resname') or link.get('wr_name', '')
                    bcpage += f'<span itemprop="name" style="font-size:12px;line-height:13px;"><strong>{wr_name}</strong></span><br>\n'
                    
                    # Address is only shown when address exists and map == 1 (PHP line 559)
                    if address and map_val == 1 and stadd:
                        bcpage += '<div itemprop="address" itemscope itemtype="http://schema.org/PostalAddress">\n'
                        bcpage += f'<span style="font-size:12px;line-height:13px;" itemprop="streetAddress">{stadd}</span><br>\n'
                        bcpage += f'<span style="font-size:12px;line-height:13px;" itemprop="addressLocality">{cty}</span> '
                        bcpage += f'<span style="font-size:12px;line-height:13px;" itemprop="addressRegion">{state}</span> '
                        bcpage += f'<span style="font-size:12px;line-height:13px;" itemprop="postalCode">{zip_code}</span>\n'
                        bcpage += f'<span style="font-size:12px;line-height:13px;display:none;" itemprop="addressCountry">{link.get("domain_country", "")}</span><br>\n'
                    
                    if link.get('wr_phone') or link.get('resphone'):
                        phon = link.get('resphone') or link.get('wr_phone', '')
                        bcpage += f'<span style="font-size:12px;line-height:13px;" itemprop="telephone">{phon}<br>\n'
                    
                    bcpage += f'<a style="font-size:12px;line-height:13px;" itemprop="url" href="{linkalone}">{link["domain_name"]}</a></span><br>\n'
                    
                    if address and map_val == 1:
                        bcpage += '</div>\n'
                    
                    # Social media icons
                    if (link.get('wr_googleplus') or link.get('wr_facebook') or link.get('wr_twitter') or 
                        link.get('wr_linkedin') or link.get('wr_yelp') or link.get('wr_bing') or link.get('wr_yahoo')):
                        bcpage += '<div class="seo-automation-space"></div>\n'
                        alttxt = seo_filter_text_custom(link.get('restitle', ''))
                        bcpage += '<div class="related-art-social">\n'
                        
                        # Add all social icons
                        if link.get('wr_facebook'):
                            urlf = link['wr_facebook']
                            if 'http' in urlf:
                                urlf = urlf.replace('http:', 'https:')
                            elif urlf.startswith('/'):
                                urlf = 'https://www.facebook.com' + urlf
                            else:
                                urlf = 'https://www.facebook.com/' + urlf
                            bcpage += f'<a href="{urlf}" title="{alttxt} - Follow us on Facebook" target="_blank"><img src="//imagehosting.space/images/fbfavicon.ico" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_twitter'):
                            urlt = link['wr_twitter']
                            if 'http' in urlt:
                                urlt = urlt.replace('http:', 'https:')
                            elif urlt.startswith('/'):
                                urlt = 'https://twitter.com' + urlt
                            else:
                                urlt = 'https://twitter.com/' + urlt
                            bcpage += f'<a href="{urlt}" title="{alttxt} - Follow us on Twitter" target="_blank"><img src="//imagehosting.space/images/twitfavicon.ico" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_linkedin'):
                            urll = link['wr_linkedin']
                            if 'http' in urll:
                                urll = urll.replace('http:', 'https:')
                            elif urll.startswith('/'):
                                urll = 'https://www.linkedin.com/pub' + urll
                            else:
                                urll = 'https://www.linkedin.com/pub/' + urll
                            bcpage += f'<a href="{urll}" title="{alttxt} - Follow us on LinkedIn" target="_blank"><img src="//imagehosting.space/images/linkfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_googleplus'):
                            urlg = link['wr_googleplus']
                            if 'http' in urlg:
                                urlg = urlg.replace('http:', 'https:')
                            elif urlg.startswith('/'):
                                urlg = 'https://plus.google.com' + urlg
                            else:
                                urlg = 'https://plus.google.com/' + urlg
                            bcpage += f'<a href="{urlg}" title="{alttxt} - Find us on Google" target="_blank"><img src="//imagehosting.space/images/maps15_bnuw3a_32dp.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_yelp'):
                            urly = link['wr_yelp']
                            bcpage += f'<a href="{urly}" title="{alttxt} - Follow us on Yelp" target="_blank"><img src="//imagehosting.space/images/yelpfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_bing'):
                            urly = link['wr_bing']
                            bcpage += f'<a href="{urly}" title="{alttxt} - Find us on Bing" target="_blank"><img src="//imagehosting.space/images/bingfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_yahoo'):
                            urly = link['wr_yahoo']
                            bcpage += f'<a href="{urly}" title="{alttxt} - Find us on Yahoo" target="_blank"><img src="//imagehosting.space/images/yahoofavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        bcpage += '</div>\n'
                    
                    if link_settings.get('blogUrl') and len(link_settings['blogUrl']) > 10:
                        bcpage += f' <a target="_blank" href="{link_settings["blogUrl"]}">Blog</a>  '
                    if link_settings.get('faqUrl') and len(link_settings['faqUrl']) > 10:
                        bcpage += f' <a target="_blank" href="{link_settings["faqUrl"]}">FAQ</a> '
                    
                    bcpage += '</div>\n'
                    bcpage += '</div>\n'
                else:
                    # No address - just image
                    bcpage += '<div class="snapshot-container" style="margin-left:20px !important;">\n'
                    bcpage += f'<a href="{imageurl}" target="_blank"{follow}><img src="//imagehosting.space/feed/pageimage.php?domain={link["domain_name"]}" alt="{link["domain_name"]}" style="width:130px !important;height:110px;"></a>\n'
                    if link_settings.get('blogUrl') and len(link_settings['blogUrl']) > 10:
                        bcpage += f' <a target="_blank" href="{link_settings["blogUrl"]}">Blog</a>  '
                    if link_settings.get('faqUrl') and len(link_settings['faqUrl']) > 10:
                        bcpage += f' <a target="_blank" href="{link_settings["faqUrl"]}">FAQ</a> '
                    bcpage += '</div>\n'
                
                # Build text content
                if link.get('resname'):
                    wr_name = link['resname']
                else:
                    wr_name = link.get('wr_name', '')
                
                if link.get('restitle') and not is_bron(link.get('servicetype')):
                    restextkw = seo_filter_text_custom(link['restitle'])
                elif wr_name:
                    restextkw = seo_filter_text_custom(wr_name)
                else:
                    restextkw = seo_filter_text_custom(link.get('domain_name', ''))
                
                if link.get('desc2') and not link.get('resshorttext'):
                    restext = seo_filter_text_custom(link['desc2'])
                else:
                    restext = seo_filter_text_custom(link.get('resshorttext', ''))
                
                if len(restext) < 20:
                    restext = restextkw
                
                # Trim to first 100 words (PHP trimToFirst100Words)
                words = restext.split()[:100]
                restext = ' '.join(words)
                
                # Add link to text - match PHP logic exactly
                # PHP line 714-741: Complex conditional logic for adding links to text
                addrndfeed = 0
                if map_val == 1:
                    # PHP line 714-715: map == 1
                    # Use seo_automation_add_text_link_newbc equivalent
                    restext = seo_automation_add_text_link_newbc(restext, restextkw, imageurl, follow)
                elif preml == 1:
                    # PHP line 716-717: preml == 1
                    restext = seo_automation_add_text_link_newbc(restext, restextkw, '', follow)
                elif (link.get('status') == '8' and haslinkspg_count > 1) or (addrndfeed == 1 and haslinkspg_count > 1):
                    # PHP line 718-738: Orphan link handling
                    orphan_sql = """
                        SELECT l.id, l.showonpgid, b.restitle, b.id AS bubblefeedid 
                        FROM bwp_link_placement l 
                        LEFT JOIN bwp_bubblefeed b ON b.id = l.showonpgid AND b.deleted != 1 
                        WHERE l.deleted != 1 AND b.restitle <> '' AND b.id != %s AND l.showondomainid = %s 
                        ORDER BY RAND() LIMIT 1
                    """
                    orphanlinkspg = db.fetch_row(orphan_sql, (haslinkspg.get('bubblefeedid', ''), link['id']))
                    if orphanlinkspg and link.get('wp_plugin') != 1:
                        # PHP line 721-726: Non-WP plugin orphan link
                        script_version_num = get_script_version_num(link.get('script_version'))
                        if script_version_num >= 3 and link.get('wp_plugin') != 1 and link.get('iswin') != 1 and link.get('usepurl') != 0:
                            orphlink = linkdomain + '/' + bcvardomain + '/' + seo_slug(seo_filter_text_custom(orphanlinkspg.get('restitle', ''))) + '/' + str(orphanlinkspg.get('bubblefeedid', '')) + 'bc/'
                        else:
                            # CodeURL equivalent - simplified
                            orphlink = linkdomain + '/?Action=2&k=' + seo_slug(seo_filter_text_custom(orphanlinkspg.get('restitle', '')))
                    elif orphanlinkspg and link.get('wp_plugin') == 1:
                        # PHP line 728-733: WP plugin orphan link
                        if is_bron(link.get('servicetype')):
                            orphlink = linkdomain + '/' + str(orphanlinkspg.get('showonpgid', '')) + 'bc/'
                        else:
                            import html
                            slug_text = seo_text_custom(orphanlinkspg.get('restitle', ''))
                            slug_text = html.unescape(slug_text)
                            slug_text = to_ascii(slug_text)
                            slug_text = slug_text.lower()
                            slug_text = slug_text.replace(' ', '-')
                            orphlink = linkdomain + '/' + slug_text + '-' + str(orphanlinkspg.get('showonpgid', '')) + 'bc/'
                    else:
                        orphlink = linkalone
                    restext = seo_automation_add_text_link_newbc(restext, restextkw, orphlink, follow)
                else:
                    # PHP line 740-741: Default fallback
                    restext = seo_automation_add_text_link_newbc(restext, restextkw, linkalone, follow)
                
                bcpage += restext + '\n'
                
                # Social media if no address
                if preml == 0:
                    if (link.get('wr_googleplus') or link.get('wr_facebook') or link.get('wr_twitter') or 
                        link.get('wr_linkedin') or link.get('wr_yelp') or link.get('wr_bing') or link.get('wr_yahoo')):
                        bcpage += '<div style="height:1px;"></div>\n'
                        alttxt = seo_filter_text_custom(link.get('restitle', ''))
                        bcpage += '<div class="related-art-social" style="float:left;">\n'
                        
                        # Add all social icons
                        if link.get('wr_facebook'):
                            urlf = link['wr_facebook']
                            if 'http' in urlf:
                                urlf = urlf.replace('http:', 'https:')
                            elif urlf.startswith('/'):
                                urlf = 'https://www.facebook.com' + urlf
                            else:
                                urlf = 'https://www.facebook.com/' + urlf
                            bcpage += f'<a href="{urlf}" title="{alttxt} - Follow us on Facebook" target="_blank"><img src="//imagehosting.space/images/fbfavicon.ico" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_twitter'):
                            urlt = link['wr_twitter']
                            if 'http' in urlt:
                                urlt = urlt.replace('http:', 'https:')
                            elif urlt.startswith('/'):
                                urlt = 'https://twitter.com' + urlt
                            else:
                                urlt = 'https://twitter.com/' + urlt
                            bcpage += f'<a href="{urlt}" title="{alttxt} - Follow us on Twitter" target="_blank"><img src="//imagehosting.space/images/twitfavicon.ico" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_linkedin'):
                            urll = link['wr_linkedin']
                            if 'http' in urll:
                                urll = urll.replace('http:', 'https:')
                            elif urll.startswith('/'):
                                urll = 'https://www.linkedin.com/pub' + urll
                            else:
                                urll = 'https://www.linkedin.com/pub/' + urll
                            bcpage += f'<a href="{urll}" title="{alttxt} - Follow us on LinkedIn" target="_blank"><img src="//imagehosting.space/images/linkfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_googleplus'):
                            urlg = link['wr_googleplus']
                            if 'http' in urlg:
                                urlg = urlg.replace('http:', 'https:')
                            elif urlg.startswith('/'):
                                urlg = 'https://plus.google.com' + urlg
                            else:
                                urlg = 'https://plus.google.com/' + urlg
                            bcpage += f'<a href="{urlg}" title="{alttxt} - Find us on Google" target="_blank"><img src="//imagehosting.space/images/maps15_bnuw3a_32dp.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_yelp'):
                            urly = link['wr_yelp']
                            bcpage += f'<a href="{urly}" title="{alttxt} - Follow us on Yelp" target="_blank"><img src="//imagehosting.space/images/yelpfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_bing'):
                            urly = link['wr_bing']
                            bcpage += f'<a href="{urly}" title="{alttxt} - Find us on Bing" target="_blank"><img src="//imagehosting.space/images/bingfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        if link.get('wr_yahoo'):
                            urly = link['wr_yahoo']
                            bcpage += f'<a href="{urly}" title="{alttxt} - Find us on Yahoo" target="_blank"><img src="//imagehosting.space/images/yahoofavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                        
                        bcpage += '</div>\n'
                
                # PHP line 1336: Close container and add spacer
                bcpage += f'</div><div class="{css_prefix}-spacer"></div>\n'
    
    # Drip content links section
    linksdc_sql = """
        SELECT d.*, b.id AS bubbafeedid, b.bubblefeedid, b.restitle, b.bubbatitle, b.resshorttext, b.resfulltext, 
               b.linkouturl, b.resaddress, b.resphone, l.linkformat, l.deeplink, l.relevant,
               s.servicetype AS servicename, s.price,
               c.category AS subcat,
               mc.maincategories_name AS maincat,
               d.showtagsonbusinesscollective, d.usewebsitereferencetitles
        FROM bwp_link_placement l
        LEFT JOIN bwp_domains d ON d.id = l.domainid
        LEFT JOIN bwp_services s ON d.servicetype = s.id
        LEFT JOIN bwp_bubbafeed b ON b.id = l.bubblefeedid
        LEFT JOIN bwp_bubblefeed bl ON bl.id = b.bubblefeedid
        LEFT JOIN bwp_domain_category c ON c.id = d.domain_category
        LEFT JOIN bwp_maincategories mc ON mc.maincategories_id = c.parent_catid
        WHERE l.showondomainid = %s
        AND l.showonpgid = %s
        AND l.deleted != 1
        AND d.deleted != 1
        AND b.deleted != 1
        AND bl.deleted != 1
        AND l.linkformat = 'dripcontent'
        AND l.showondomainid NOT IN (SELECT domain_id FROM bwp_domains_disabled WHERE disabled_domain_id = d.id)
        AND d.domainip != %s
        ORDER BY l.relevant DESC
    """
    linksdc = db.fetch_all(linksdc_sql, (domainid, res['id'], domain_data.get('domainip', '')))
    
    if linksdc:
        for linkdc in linksdc:
            # Build link domain
            if linkdc.get('ishttps') == 1:
                lprfx = 'https://'
            else:
                lprfx = 'http://'
            if linkdc.get('usewww') == 1:
                linkdomain = lprfx + 'www.' + linkdc['domain_name']
            else:
                linkdomain = lprfx + linkdc['domain_name']
            
            linkdomainalone = linkdomain
            if linkdc.get('servicetype') == 370:
                linkdomainalone = linkdomain + '/'
            
            bcdomain = linkdc['domain_name'].split('.')
            bcvardomain = bcdomain[0] if bcdomain else ''
            
            bcpage += f'<div class="{css_prefix}-container">\n'
            # PHP line 399: Add spacer right after opening container (before H2)
            bcpage += f'<div class="{css_prefix}-spacer"></div>\n'
            
            # Build link URL - match PHP logic exactly
            # PHP line 895-927: Complex conditional logic for drip content link URL
            if len(linkdc.get('linkouturl', '')) > 5 and linkdc.get('status') in ['2', '10']:
                # PHP line 895-897
                linkurl = linkdc['linkouturl'].strip()
            elif linkdc.get('skipfeedchecker') == 1 and linkdc.get('linkskipfeedchecker') != 1:
                # PHP line 899-902
                linkurl = linkdomainalone
            elif linkdc.get('wp_plugin') == 1 and len(linkdc.get('resfulltext') or '') >= 300:
                # PHP line 904-906: Use toAscii(html_entity_decode(seo_text_custom(...)))
                import html
                slug_text = seo_text_custom(linkdc.get('bubbatitle', ''))
                slug_text = html.unescape(slug_text)
                slug_text = to_ascii(slug_text)
                slug_text = slug_text.lower()
                slug_text = slug_text.replace(' ', '-')
                linkurl = linkdomain + '/' + slug_text + '-' + str(linkdc.get('bubbafeedid', '')) + 'dc'
            elif linkdc.get('wp_plugin') != 1 and len(linkdc.get('resfulltext') or '') >= 50 and linkdc.get('status') in ['2', '10']:
                # PHP line 908-913: Non-WP plugin
                script_version_num = get_script_version_num(linkdc.get('script_version'))
                if script_version_num > 3.2 and linkdc.get('wp_plugin') != 1 and linkdc.get('iswin') != 1 and linkdc.get('usepurl') != 0:
                    linkurl = linkdomain + '/' + bcvardomain + '/' + seo_slug(seo_filter_text_custom(linkdc.get('bubbatitle', ''))) + '/' + str(linkdc.get('bubbafeedid', '')) + 'dc'
                else:
                    # CodeURL equivalent - simplified
                    linkurl = linkdomain + '/?Action=3&k=' + seo_slug(seo_filter_text_custom(linkdc.get('bubbatitle', ''))) + '&PageID=' + str(linkdc.get('bubbafeedid', ''))
            else:
                # PHP line 924-926: Default fallback
                linkurl = linkdomainalone
            
            follow = ' rel="nofollow"' if linkdc.get('forceinboundnofollow') == 1 else ''
            stitle = clean_title(seo_filter_text_custom(linkdc.get('bubbatitle', '')))
            
            bcpage += f'<h2 class="h2"><a title="{stitle}" href="{linkurl}" style="text-align:left;" target="_blank"{follow}>{stitle}</a></h2>\n'
            
            # Build image URL - match PHP logic exactly
            # PHP line 934-950: Complex conditional logic for drip content image URL
            haslinks_dc_sql = "SELECT count(id) FROM bwp_link_placement WHERE deleted != 1 AND showondomainid = %s AND showonpgid = %s"
            haslinks_dc = db.fetch_one(haslinks_dc_sql, (linkdc['id'], linkdc.get('bubblefeedid')))
            haslinks_dc = haslinks_dc or 0
            
            if haslinks_dc >= 1:
                haslinkspg_dc = {'restitle': linkdc.get('restitle'), 'showonpgid': linkdc.get('bubblefeedid'), 'bubblefeedid': linkdc.get('bubblefeedid')}
            else:
                haslinkspg_dc_sql = """
                    SELECT l.id, l.showonpgid, b.restitle, b.id AS bubblefeedid 
                    FROM bwp_link_placement l 
                    LEFT JOIN bwp_bubblefeed b ON b.id = l.showonpgid AND b.deleted != 1 
                    WHERE l.deleted != 1 AND b.restitle <> '' AND l.showondomainid = %s 
                    ORDER BY RAND() LIMIT 1
                """
                haslinkspg_dc = db.fetch_row(haslinkspg_dc_sql, (linkdc['id'],))
                if not haslinkspg_dc:
                    haslinkspg_dc = {}
            
            haslinkspg_dc_count = haslinks_dc if haslinks_dc else 0
            
            if linkdc.get('skipfeedchecker') == 1 and linkdc.get('linkskipfeedchecker') != 1:
                # PHP line 934-936
                imageurl = linkdomainalone
            elif haslinkspg_dc_count > 0 and linkdc.get('wp_plugin') != 1 and linkdc.get('status') in ['2', '10', '8']:
                # PHP line 938-943: Non-WP plugin with haslinkspg
                script_version_num = get_script_version_num(linkdc.get('script_version'))
                if script_version_num > 3.2 and linkdc.get('wp_plugin') != 1 and linkdc.get('iswin') != 1 and linkdc.get('usepurl') != 0:
                    imageurl = linkdomain + '/' + bcvardomain + '/' + seo_slug(seo_filter_text_custom(haslinkspg_dc.get('restitle', ''))) + '/' + str(haslinkspg_dc.get('bubblefeedid', '')) + 'bc/'
                else:
                    # CodeURL equivalent - simplified
                    imageurl = linkdomain + '/?Action=2&k=' + seo_slug(seo_filter_text_custom(haslinkspg_dc.get('restitle', '')))
            elif haslinkspg_dc_count > 0 and linkdc.get('wp_plugin') == 1 and linkdc.get('status') in ['2', '10', '8']:
                # PHP line 945-947: WP plugin with haslinkspg - use toAscii(html_entity_decode(seo_text_custom(...)))
                import html
                slug_text = seo_text_custom(haslinkspg_dc.get('restitle', ''))
                slug_text = html.unescape(slug_text)
                slug_text = to_ascii(slug_text)
                slug_text = slug_text.lower()
                slug_text = slug_text.replace(' ', '-')
                imageurl = linkdomain + '/' + slug_text + '-' + str(haslinkspg_dc.get('showonpgid', '')) + 'bc/'
            else:
                # PHP line 949-950: Default fallback
                imageurl = linkdomainalone
            
            # Build text content
            wr_name = linkdc.get('wr_name', '')
            if linkdc.get('restitle'):
                restextkw = seo_filter_text_custom(linkdc['restitle'])
            elif wr_name:
                restextkw = seo_filter_text_custom(wr_name)
            else:
                restextkw = seo_filter_text_custom(linkdc.get('domain_name', ''))
            
            # Get bubbatext
            bubbatext = linkdc.get('resfulltext', '')
            if bubbatext:
                bubbatext = html.unescape(bubbatext)
                # Strip tags except img (PHP: strip_tags with '<img>' allowed)
                bubbatext = re.sub(r'<(?!img\b)[^>]+>', '', bubbatext)
                # Shorten to 75 characters (PHP: bwp_shorten_string($bubbatext,75))
                if len(bubbatext) > 75:
                    bubbatext = bubbatext[:75].rsplit(' ', 1)[0] + '...'
                # Replace gallery URLs
                bubbatext = bubbatext.replace('//gallery.imagehosting.space/gallery/', '//gallery.imagehosting.space/thumbs/')
                # Wrap images in links (PHP: preg_replace pattern)
                bubbatext = re.sub(r'(?<!<a\s[^>]*>)(<img[^>]+>)(?!</a>)', f'<a href="{imageurl}">\\1</a>', bubbatext)
                # Add keyword link using seo_automation_add_text_link_newbc
                # PHP line 1215: Uses seo_automation_add_text_link_newbc
                bubbatext = seo_automation_add_text_link_newbc(bubbatext, restextkw, linkurl, follow)
            
            bcpage += bubbatext + '\n'
            
            # Social media if no address
            if (linkdc.get('wr_googleplus') or linkdc.get('wr_facebook') or linkdc.get('wr_twitter') or 
                linkdc.get('wr_linkedin') or linkdc.get('wr_yelp') or linkdc.get('wr_bing') or linkdc.get('wr_yahoo')):
                bcpage += '<div style="height:1px;"></div>\n'
                alttxt = seo_filter_text_custom(linkdc.get('restitle', ''))
                bcpage += '<div class="related-art-social" style="float:left;">\n'
                
                # Add all social icons
                if linkdc.get('wr_facebook'):
                    urlf = linkdc['wr_facebook']
                    if 'http' in urlf:
                        urlf = urlf.replace('http:', 'https:')
                    elif urlf.startswith('/'):
                        urlf = 'https://www.facebook.com' + urlf
                    else:
                        urlf = 'https://www.facebook.com/' + urlf
                    bcpage += f'<a href="{urlf}" title="{alttxt} - Follow us on Facebook" target="_blank"><img src="//imagehosting.space/images/fbfavicon.ico" width="16" alt="{alttxt}"></a>'
                
                if linkdc.get('wr_twitter'):
                    urlt = linkdc['wr_twitter']
                    if 'http' in urlt:
                        urlt = urlt.replace('http:', 'https:')
                    elif urlt.startswith('/'):
                        urlt = 'https://twitter.com' + urlt
                    else:
                        urlt = 'https://twitter.com/' + urlt
                    bcpage += f'<a href="{urlt}" title="{alttxt} - Follow us on Twitter" target="_blank"><img src="//imagehosting.space/images/twitfavicon.ico" width="16" alt="{alttxt}"></a>'
                
                if linkdc.get('wr_linkedin'):
                    urll = linkdc['wr_linkedin']
                    if 'http' in urll:
                        urll = urll.replace('http:', 'https:')
                    elif urll.startswith('/'):
                        urll = 'https://www.linkedin.com/pub' + urll
                    else:
                        urll = 'https://www.linkedin.com/pub/' + urll
                    bcpage += f'<a href="{urll}" title="{alttxt} - Follow us on LinkedIn" target="_blank"><img src="//imagehosting.space/images/linkfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                
                if linkdc.get('wr_googleplus'):
                    urlg = linkdc['wr_googleplus']
                    if 'http' in urlg:
                        urlg = urlg.replace('http:', 'https:')
                    elif urlg.startswith('/'):
                        urlg = 'https://plus.google.com' + urlg
                    else:
                        urlg = 'https://plus.google.com/' + urlg
                    bcpage += f'<a href="{urlg}" title="{alttxt} - Find us on Google" target="_blank"><img src="//imagehosting.space/images/maps15_bnuw3a_32dp.ico" border="0" width="16" alt="{alttxt}"></a>'
                
                if linkdc.get('wr_yelp'):
                    urly = linkdc['wr_yelp']
                    bcpage += f'<a href="{urly}" title="{alttxt} - Follow us on Yelp" target="_blank"><img src="//imagehosting.space/images/yelpfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                
                if linkdc.get('wr_bing'):
                    urly = linkdc['wr_bing']
                    bcpage += f'<a href="{urly}" title="{alttxt} - Find us on Bing" target="_blank"><img src="//imagehosting.space/images/bingfavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                
                if linkdc.get('wr_yahoo'):
                    urly = linkdc['wr_yahoo']
                    bcpage += f'<a href="{urly}" title="{alttxt} - Find us on Yahoo" target="_blank"><img src="//imagehosting.space/images/yahoofavicon.ico" border="0" width="16" alt="{alttxt}"></a>'
                
                bcpage += '</div>\n'
            
            # PHP line 775: Close container and add spacer
            bcpage += f'</div><div class="{css_prefix}-spacer"></div>\n'
    
    # Add ArticleLinks (PHP line 1680: echo ArticleLinks($res['id']))
    # Only add ArticleLinks for non-WordPress plugin calls (PHP plugin calls)
    if domain_data.get('wp_plugin') != 1:
        # Get domain_category for ArticleLinks (it's the same as domain_data in this context)
        domain_category = domain_data
        article_links_html = build_article_links(
            pageid=bubbleid or 0,
            domainid=domainid,
            domain_data=domain_data,
            domain_settings=domain_settings,
            domain_category=domain_category
        )
        bcpage += article_links_html
    
    # Closing HTML
    bcpage += f'<div class="{css_prefix}-spacer"></div>\n'
    bcpage += f'<div class="{css_prefix}-tag-container" style="border-bottom:1px solid black; border-top:1px solid black;"></div>\n'
    bcpage += '<link rel="stylesheet" id="SEO_Automation_premium_0_X-css" href="https://public.imagehosting.space/external_files/premiumstyles.css" type="text/css" media="all" />\n'
    bcpage += '<div class="seo-automation-spacer"></div>\n'
    bcpage += '</div>\n'
    bcpage += '''<style>
.ngodkrbsitr-spacer{clear:both;}
.citation_map_container iframe {
	width:130px !important;
}
.vid-container iframe {
	width:100% !important;
}
</style>
'''
    
    return bcpage


def build_bubba_page_wp(
    bubbleid: int,
    domainid: int,
    debug: bool,
    agent: str,
    keyword: str,
    domain_data: Dict[str, Any],
    domain_settings: Dict[str, Any]
) -> str:
    """
    Build Bubba page HTML (Action=3).
    Replicates seo_automation_build_bubba_page from websitereferencebubba-wp.php
    
    TODO: Full implementation needed - this is a placeholder
    """
    if not bubbleid or not domainid:
        return ""
    
    # Get bubbafeed data
    sql = """
        SELECT ba.*, c.category, c.bubblefeedid AS catbubbleid, bb.categoryid
        FROM bwp_bubbafeed ba
        LEFT JOIN bwp_bubblefeed bb ON bb.id = ba.bubblefeedid
        LEFT JOIN bwp_bubblefeedcategory c ON c.id = bb.categoryid AND c.deleted != 1
        WHERE ba.id = %s AND ba.domainid = %s AND bb.deleted != 1 AND ba.deleted != 1
    """
    res = db.fetch_row(sql, (bubbleid, domainid))
    
    if not res:
        # Try by keyword
        sql = """
            SELECT ba.*, c.category, c.bubblefeedid AS catbubbleid, bb.categoryid
            FROM bwp_bubbafeed ba
            LEFT JOIN bwp_bubblefeed bb ON bb.id = ba.bubblefeedid
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = bb.categoryid AND c.deleted != 1
            WHERE ba.bubbatitle = %s AND ba.domainid = %s AND bb.deleted != 1 AND ba.deleted != 1
        """
        res = db.fetch_row(sql, (keyword, domainid))
    
    if not res:
        return ""
    
    # Get CSS class prefix based on wp_plugin
    css_prefix = get_css_class_prefix(domain_data.get('wp_plugin', 0))
    
    # Build basic page HTML (placeholder - needs full implementation)
    import html
    wpage = f'<div class="{css_prefix}-main-table">'
    wpage += f'<h1>{clean_title(seo_filter_text_custom(res.get("bubbatitle", "")))}</h1>'
    
    if res.get('resfulltext'):
        # Unescape HTML entities
        content = html.unescape(str(res['resfulltext']))
        wpage += f'<div class="seo-content">{content}</div>'
    
    wpage += '</div>'
    
    return wpage


def code_url(domainid: int, domain_data: Dict[str, Any], domain_settings: Dict[str, Any]) -> str:
    """
    Build CodeURL for a domain (replicates PHP CodeURL function).
    PHP CodeURL from functions.inc.php line 1998-2038.
    """
    url = ''
    
    if domain_settings.get('usedurl') == 1 and domain_data.get('domain_url'):
        url = domain_data['domain_url'].rstrip('/')
    else:
        # Build FQDN equivalent
        if domain_data.get('ishttps') == 1:
            url = 'https://'
        else:
            url = 'http://'
        if domain_data.get('usewww') == 1:
            url += 'www.' + domain_data['domain_name']
        else:
            url += domain_data['domain_name']
    
    # Add path based on domain settings
    if domain_data.get('uses0308'):
        url += '/0308'
    elif domain_settings.get('usescontent_resource'):
        url += '/content_resource'
    else:
        filename = domain_data['domain_name'].split('.')
        if filename:
            url += '/' + filename[0]
    
    # Add script extension (simplified - would need ScriptExtLookup)
    # For now, assume .php
    url += '.php'
    
    return url


def build_article_links(pageid: int, domainid: int, domain_data: Dict[str, Any], domain_settings: Dict[str, Any], domain_category: Dict[str, Any]) -> str:
    """
    Build ArticleLinks HTML (replicates PHP ArticleLinks function).
    PHP ArticleLinks from functions.inc.php line 1527-1995.
    Called via echocr(ArticleLinks($pageid)) in websitereference.php line 1560 and businesscollective.php line 1680.
    """
    import html
    from datetime import datetime
    
    # Get service labels (PHP lines 1538-1544)
    servicetype = domain_data.get('servicetype')
    labels_sql = """
        SELECT price, 
               CASE WHEN IFNULL(resources_label, '') = '' THEN 'Website Reference' ELSE resources_label END AS websitereference,
               CASE WHEN IFNULL(webring_feed_label, '') = '' THEN 'Business Log' ELSE webring_feed_label END AS businesslog,
               CASE WHEN IFNULL(business_collective_label, '') = '' THEN 'Business Collective' ELSE business_collective_label END AS businesscollective,
               CASE WHEN IFNULL(spyder_map_label, '') = '' THEN 'Sitemap' ELSE spyder_map_label END AS sitemap,
               CASE WHEN IFNULL(related_articles_label, '') = '' THEN 'Related Articles' ELSE related_articles_label END AS pubsharing
        FROM bwp_services WHERE id = %s LIMIT 1
    """
    labels = db.fetch_row(labels_sql, (servicetype,))
    if not labels:
        labels = {
            'price': 0,
            'websitereference': 'Website Reference',
            'businesslog': 'Business Log',
            'businesscollective': 'Business Collective',
            'sitemap': 'Sitemap',
            'pubsharing': 'Related Articles'
        }
    
    # Convert price to number (database may return string)
    price_raw = labels.get('price', 0)
    try:
        price = float(price_raw) if price_raw else 0
    except (ValueError, TypeError):
        price = 0
    feedlinks = ''
    
    # Build link domain (PHP lines 1561-1568)
    if domain_data.get('ishttps') == 1:
        linkdomain = 'https://'
    else:
        linkdomain = 'http://'
    if domain_data.get('usewww') == 1:
        linkdomain += 'www.' + domain_data['domain_name']
    else:
        linkdomain += domain_data['domain_name']
    
    # Get vardomain (PHP line 1618-1619)
    cdomain = domain_data['domain_name'].split('.')
    vardomain = cdomain[0] if cdomain else ''
    
    num_lnks = 0
    domain_status = domain_data.get('status')
    domain_status_str = str(domain_status) if domain_status is not None else ''
    
    # PHP lines 1623-1835: Build silo links for status 2, 10, 4, 1
    if domain_status_str in ['2', '10', '4', '1']:
        silo_sql = """
            SELECT b.restitle, b.id, b.linkouturl, b.categoryid, c.category, c.bubblefeedid, 
                   b.resfulltext, b.resshorttext, b.NoContent,
                   (SELECT COUNT(*) FROM bwp_link_placement WHERE showonpgid = b.id AND deleted != 1) AS links_per_page
            FROM bwp_bubblefeed b
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != '1'
            WHERE b.domainid = %s AND b.deleted != '1'
            ORDER BY b.restitle
        """
        silo = db.fetch_all(silo_sql, (domainid,))
        
        if silo:
            feedlinks += '<li>'
            sssnav = ''
            feedlinks += '<ul class="mdubgwi-sub-nav">\n'
            
            for item in silo:
                bubblefeedid = item.get('bubblefeedid', '')
                item_id = item.get('id')
                
                # PHP line 1644: if(strlen($silo[$i]['bubblefeedid']) == 0)
                if not bubblefeedid or len(str(bubblefeedid)) == 0:
                    links_per_page = item.get('links_per_page', 0) or 0
                    
                    # Always build Resources link regardless of links_per_page
                    bclink = code_url(domainid, domain_data, domain_settings) + '?Action=2&amp;k=' + seo_slug(seo_filter_text_custom(item.get('restitle', '')))
                    newsf = f' <a style="padding-left: 0px !important;" href="{bclink}">Resources</a>'
                    
                    if links_per_page >= 1:
                        # Get related links (PHP lines 1651-1690)
                        links_sql = """
                            SELECT l.*, d.linkexchange, d.contentshare, d.status, d.linkskipfeedchecker, d.servicetype, b.linkouturl, b.restitle
                            FROM bwp_link_placement l
                            LEFT JOIN bwp_bubblefeed b ON b.id = l.bubblefeedid
                            LEFT JOIN bwp_domains d ON d.id = l.domainid
                            WHERE l.showonpgid = %s
                            AND d.servicetype != 356
                            AND d.status IN (2,10)
                            AND d.contentshare = 1
                            AND d.linkexchange = 1
                            AND (d.skipfeedchecker != 1 OR (d.skipfeedchecker = 1 AND d.linkskipfeedchecker = 1))
                            AND (b.linkouturl IS NULL OR b.linkouturl = '')
                            AND CHAR_LENGTH(b.resfulltext) > 500 AND b.resfulltext IS NOT NULL
                        """
                        links = db.fetch_all(links_sql, (item_id,))
                        for link in links:
                            # Fetch domain data for CodeURL
                            link_domain_sql = "SELECT id, domain_name, uses0308, usescontent_resource, usewww, domain_url FROM bwp_domains WHERE id = %s"
                            link_domain = db.fetch_row(link_domain_sql, (link['id'],))
                            if link_domain:
                                link_domain_settings_sql = "SELECT * FROM bwp_domain_settings WHERE domainid = %s"
                                link_domain_settings = db.fetch_row(link_domain_settings_sql, (link['id'],))
                                if not link_domain_settings:
                                    db.execute("INSERT INTO bwp_domain_settings SET domainid = %s", (link['id'],))
                                    link_domain_settings = db.fetch_row(link_domain_settings_sql, (link['id'],))
                                linkurl = code_url(link['id'], link_domain, link_domain_settings or {})
                            else:
                                linkurl = ''
                            slug = seo_slug(seo_filter_text_custom(link.get('restitle', '')))
                            sssnav += f'<li><a style="padding-right: 0px !important;" href="{linkurl}?Action=1&amp;k={slug}&amp;PageID={link.get("bubblefeedid", "")}"> {clean_title(seo_filter_text_custom(link.get("restitle", "")))} </a></li>\n'
                        
                        # Offsite links (PHP lines 1671-1690)
                        linkso_sql = """
                            SELECT l.*, d.linkexchange, d.contentshare, d.status, d.linkskipfeedchecker, d.servicetype, b.linkouturl, b.restitle
                            FROM bwp_link_placement l
                            LEFT JOIN bwp_bubblefeedoffsite bo ON bo.id = l.bubblefeedid
                            LEFT JOIN bwp_bubblefeed b ON b.id = bo.bubblefeedid
                            LEFT JOIN bwp_domains d ON d.id = l.domainid
                            WHERE l.showonpgid = %s
                            AND l.linkformat = 'offsite'
                            AND d.servicetype != 356
                            AND d.status IN (2,10)
                            AND d.contentshare = 1
                            AND d.linkexchange = 1
                            AND (d.skipfeedchecker != 1 OR (d.skipfeedchecker = 1 AND d.linkskipfeedchecker = 1))
                        """
                        linkso = db.fetch_all(linkso_sql, (item_id,))
                        for link in linkso:
                            # Fetch domain data for CodeURL
                            link_domain_sql = "SELECT id, domain_name, uses0308, usescontent_resource, usewww, domain_url FROM bwp_domains WHERE id = %s"
                            link_domain = db.fetch_row(link_domain_sql, (link['id'],))
                            if link_domain:
                                link_domain_settings_sql = "SELECT * FROM bwp_domain_settings WHERE domainid = %s"
                                link_domain_settings = db.fetch_row(link_domain_settings_sql, (link['id'],))
                                if not link_domain_settings:
                                    db.execute("INSERT INTO bwp_domain_settings SET domainid = %s", (link['id'],))
                                    link_domain_settings = db.fetch_row(link_domain_settings_sql, (link['id'],))
                                linkurl = code_url(link['id'], link_domain, link_domain_settings or {})
                            else:
                                linkurl = ''
                            slug = seo_slug(seo_filter_text_custom(link.get('restitle', '')))
                            sssnav += f'<li><a style="padding-right: 0px !important;" href="{linkurl}?Action=1&amp;k={slug}&amp;PageID={link.get("bubblefeedid", "")}"> {clean_title(seo_filter_text_custom(link.get("restitle", "")))} </a></li>\n'
                    
                    # Build main link (PHP lines 1700-1716)
                    # #region agent log
                    _debug_log("content.py:build_article_links", "Building main link for PHP plugin", {
                        "resourcesactive": domain_category.get('resourcesactive'),
                        "restitle": item.get('restitle', ''),
                        "item_id": item_id,
                        "linkouturl": item.get('linkouturl', '')
                    }, "A")
                    # #endregion
                    if domain_category.get('resourcesactive') == '1':
                        if item.get('NoContent') == 0 and len(item.get('linkouturl', '').strip()) > 5:
                            feedlinks += f'<li><a style="padding-right: 0px !important;" href="{item["linkouturl"]}">{clean_title(seo_filter_text_custom(item.get("restitle", "")))}</a>{newsf}</li>\n'
                        else:
                            linkurl = code_url(domainid, domain_data, domain_settings)
                            slug = seo_slug(seo_filter_text_custom(item.get('restitle', '')))
                            main_link = f'{linkurl}?Action=1&amp;k={slug}&amp;PageID={item_id}'
                            # #region agent log
                            _debug_log("content.py:build_article_links", "Generated main link (resourcesactive=1)", {
                                "main_link": main_link
                            }, "A")
                            # #endregion
                            feedlinks += f'<li><a style="padding-right: 0px !important;" href="{main_link}"> {clean_title(seo_filter_text_custom(item.get("restitle", "")))}</a>{newsf}</li>\n'
                    else:
                        linkurl = code_url(domainid, domain_data, domain_settings)
                        slug = seo_slug(seo_filter_text_custom(item.get('restitle', '')))
                        main_link = f'{linkurl}?Action=2&amp;k={slug}'
                        # #region agent log
                        _debug_log("content.py:build_article_links", "Generated main link (resourcesactive!=1)", {
                            "main_link": main_link
                        }, "A")
                        # #endregion
                        feedlinks += f'<li><a style="padding-right: 0px !important;" href="{main_link}"> {clean_title(seo_filter_text_custom(item.get("restitle", "")))}</a>{newsf}</li>\n'
                    
                    num_lnks += 1
                
                # PHP line 1723: elseif($silo[$i]['bubblefeedid'] == $silo[$i]['id'])
                elif bubblefeedid == item_id:
                    links_per_page = item.get('links_per_page', 0) or 0
                    
                    # Always build Resources link regardless of links_per_page
                    bclink = code_url(domainid, domain_data, domain_settings) + '?Action=2&amp;k=' + seo_slug(seo_filter_text_custom(item.get('restitle', '')))
                    newsf = f' <a style="padding-left: 0px !important;" href="{bclink}">Resources</a>'
                    
                    if links_per_page >= 1:
                        # Get related links (similar to above)
                        links_sql = """
                            SELECT l.*, d.linkexchange, d.contentshare, d.status, d.linkskipfeedchecker, d.servicetype, d.dripcontent, b.linkouturl, b.restitle
                            FROM bwp_link_placement l
                            LEFT JOIN bwp_bubblefeed b ON b.id = l.bubblefeedid
                            LEFT JOIN bwp_domains d ON d.id = l.domainid
                            WHERE l.showonpgid = %s
                            AND d.servicetype != 356
                            AND d.status IN (2,10)
                            AND d.contentshare = 1
                            AND d.linkexchange = 1
                            AND (d.skipfeedchecker != 1 OR (d.skipfeedchecker = 1 AND d.linkskipfeedchecker = 1))
                            AND (b.linkouturl IS NULL OR b.linkouturl = '')
                            AND CHAR_LENGTH(b.resfulltext) > 500 AND b.resfulltext IS NOT NULL
                        """
                        links = db.fetch_all(links_sql, (item_id,))
                        for link in links:
                            # Fetch domain data for CodeURL
                            link_domain_sql = "SELECT id, domain_name, uses0308, usescontent_resource, usewww, domain_url FROM bwp_domains WHERE id = %s"
                            link_domain = db.fetch_row(link_domain_sql, (link['id'],))
                            if link_domain:
                                link_domain_settings_sql = "SELECT * FROM bwp_domain_settings WHERE domainid = %s"
                                link_domain_settings = db.fetch_row(link_domain_settings_sql, (link['id'],))
                                if not link_domain_settings:
                                    db.execute("INSERT INTO bwp_domain_settings SET domainid = %s", (link['id'],))
                                    link_domain_settings = db.fetch_row(link_domain_settings_sql, (link['id'],))
                                linkurl = code_url(link['id'], link_domain, link_domain_settings or {})
                            else:
                                linkurl = ''
                            slug = seo_slug(seo_filter_text_custom(link.get('restitle', '')))
                            sssnav += f'<li><a style="padding-right: 0px !important;" href="{linkurl}?Action=1&amp;k={slug}&amp;PageID={link.get("bubblefeedid", "")}"> {clean_title(seo_filter_text_custom(link.get("restitle", "")))} </a></li>\n'
                    
                    # Build category link (PHP lines 1758-1764)
                    if domain_category.get('resourcesactive') == '1':
                        linkurl = code_url(domainid, domain_data, domain_settings)
                        category_slug = seo_slug(seo_filter_text_custom(item.get('category', '')))
                        feedlinks += f'<li><a style="padding-right: 0px !important;" href="{linkurl}?Action=1&amp;category={category_slug}&amp;c={item.get("categoryid", "")}"> {clean_title(seo_filter_text_custom(item.get("restitle", "")))}</a>{newsf}</li>\n'
                    else:
                        linkurl = code_url(domainid, domain_data, domain_settings)
                        slug = seo_slug(seo_filter_text_custom(item.get('restitle', '')))
                        feedlinks += f'<li><a style="padding-right: 0px !important;" href="{linkurl}?Action=2&amp;k={slug}"> {clean_title(seo_filter_text_custom(item.get("restitle", "")))}</a>{newsf}</li>\n'
                    
                    num_lnks += 1
                
                # PHP line 1767: elseif(strlen(trim($silo[$i]['linkouturl'])) > 5)
                elif len(item.get('linkouturl', '').strip()) > 5:
                    # Always build Resources link regardless of links_per_page
                    bclink = code_url(domainid, domain_data, domain_settings) + '?Action=2&amp;k=' + seo_slug(seo_filter_text_custom(item.get('restitle', '')))
                    newsf = f' <a style="padding-left: 0px !important;" href="{bclink}">Resources</a>'
                    feedlinks += f'<li><a style="padding-right: 0px !important;" href="{item["linkouturl"]}">{clean_title(seo_filter_text_custom(item.get("restitle", "")))}</a>{newsf}</li>\n'
            
            feedlinks += '</ul>\n'
            wrlabel = f'<a href="{code_url(domainid, domain_data, domain_settings)}?Action=1">Articles</a>'
            feedlinks += wrlabel + '</li>\n'
            
            # Add Bubba feed links (drip content) (PHP lines 1795-1823)
            dripcontent = domain_data.get('dripcontent', 0)
            if dripcontent and dripcontent > 3:
                bubba_sql = """
                    SELECT ba.*
                    FROM bwp_bubbafeed ba
                    LEFT JOIN bwp_bubblefeed bb ON bb.id = ba.bubblefeedid
                    WHERE ba.domainid = %s
                    AND ba.deleted != 1
                    AND bb.deleted != 1
                    AND bb.id IS NOT NULL
                    AND LENGTH(ba.resfulltext) > 300
                    ORDER BY ba.id DESC
                    LIMIT 20
                """
                allbubba = db.fetch_all(bubba_sql, (domainid,))
                if allbubba:
                    feedlinks += '<li>'
                    feedlinks += '<ul class="mdubgwi-sub-nav">\n'
                    for bubba in allbubba:
                        slug_text = seo_text_custom(bubba.get('bubbatitle', ''))
                        slug_text = html.unescape(slug_text)
                        slug_text = to_ascii(slug_text)
                        slug_text = slug_text.lower()
                        slug_text = slug_text.replace(' ', '-')
                        linkurl = code_url(domainid, domain_data, domain_settings) + '?Action=3&amp;k=' + slug_text + '&amp;PageID=' + str(bubba.get('id', ''))
                        feedlinks += f'<li><a style="padding-right: 0px !important;" href="{linkurl}"> {clean_title(html.unescape(seo_filter_text_custom(bubba.get("bubbatitle", ""))))} </a></li>\n'
                    feedlinks += '</ul>\n'
                    wrlabel = f'<a href="{code_url(domainid, domain_data, domain_settings)}?Action=3">Blog</a>'
                    feedlinks += wrlabel + '</li>\n'
                    num_lnks += 1
        
        # Add Blog and FAQ links (PHP lines 1827-1834)
        if domain_settings.get('blogUrl') and len(domain_settings['blogUrl']) > 10:
            feedlinks += f'<li><a class="url" style="width: 100%;font-size:12px;line-height:13px;" target="_blank" href="{domain_settings["blogUrl"]}">Blog</a></li>\n'
        if domain_settings.get('faqUrl') and len(domain_settings['faqUrl']) > 10:
            feedlinks += f'<li><a class="url" style="width: 100%;font-size:12px;line-height:13px;" target="_blank" href="{domain_settings["faqUrl"]}">FAQ</a></li>\n'
    
    # PHP lines 1837-1912: Status 8 handling (simplified)
    if domain_status_str == '8':
        # Similar logic but simplified for status 8
        silo_sql = """
            SELECT b.restitle, b.id, b.linkouturl, c.bubblefeedid, b.resfulltext, b.resshorttext,
                   (SELECT COUNT(*) FROM bwp_link_placement WHERE showonpgid = b.id AND deleted != 1) AS links_per_page
            FROM bwp_bubblefeed b
            LEFT JOIN bwp_bubblefeedcategory c ON c.id = b.categoryid AND c.deleted != '1'
            WHERE b.domainid = %s AND b.deleted != '1'
            ORDER BY b.restitle
        """
        silo = db.fetch_all(silo_sql, (domainid,))
        if silo:
            feedlinks += '<li>'
            feedlinks += '<ul class="mdubgwi-sub-nav">\n'
            for item in silo:
                script_version_num = get_script_version_num(domain_data.get('script_version'))
                if script_version_num >= 3 and domain_data.get('wp_plugin') != 1 and domain_data.get('iswin') != 1 and domain_data.get('usepurl') != 0:
                    slug = seo_slug(seo_filter_text_custom(item.get('restitle', '')))
                    feedlinks += f'<li><a style="padding-right: 0px !important;" href="{linkdomain}/{vardomain}/{slug}/{item.get("id", "")}bc/"> {clean_title(seo_filter_text_custom(item.get("restitle", "")))}</a></li>\n'
                else:
                    linkurl = code_url(domainid, domain_data, domain_settings)
                    slug = seo_slug(seo_filter_text_custom(item.get('restitle', '')))
                    feedlinks += f'<li><a href="{linkurl}?Action=2&amp;k={slug}"> {clean_title(seo_filter_text_custom(item.get("restitle", "")))}</a></li>\n'
                num_lnks += 1
            feedlinks += '</ul>\n'
            feedlinks += 'Articles</li>\n'
    
    # Build final wrapper HTML (PHP lines 1965-1992)
    ispay = 'bronze'
    if (price > 0 and domain_category.get('skipaddurllinks') == '0') or domain_category.get('skipaddurllinks') == '0' or True:
        ispay = 'gold'
        if domain_data.get('wr_name'):
            ltest = domain_data['wr_name']
        else:
            ltest = domain_data['domain_name']
        feedlinks += f'</ul><a href="{linkdomain}/"><div class="mdubgwi-button-ktue" style="background:transparent;text-align:center;white-space:nowrap;">&copy; {datetime.now().year} {ltest}</div></a><div id="mdubgwi-hidden-button"></div></li>'
    else:
        feedlinks += '</ul><a target="_blank" href="/" title="Home"><div class="mdubgwi-button"></div></a><div id="mdubgwi-hidden-button"></div></li>'
    
    feedlinks += '</ul></div>'
    
    # Wrap with outer divs (PHP line 1991)
    feedlinks = f'<div class="ngodkrbsitr-spacer"></div><div style="display:block !important;" class="mdubgwi-footer-section {ispay}"><ul class="mdubgwi-footer-nav num-{num_lnks}"><li><ul>' + feedlinks
    
    feedlinks += f'<!-- nsssnav {domain_category.get("contentshare", "")} -->'
    
    return feedlinks