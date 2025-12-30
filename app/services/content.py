"""Content generation services."""
from app.database import db
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def build_footer_wp(domainid: int, domain_data: Dict[str, Any], domain_settings: Dict[str, Any]) -> Dict[str, str]:
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
            if item.get('id'):
                # Build link
                if item.get('links_per_page', 0) >= 1:
                    # Build Resources link
                    slug = seo_slug(item['restitle']) + '-' + str(item['id']) + 'bc/'
                    bclink = linkdomain + '/' + slug
                    newsf = ' <a style="padding-left: 0px !important;" href="' + bclink + '">Resources</a>'
                else:
                    newsf = ''
                
                    if domain_data.get('resourcesactive') == '1':
                        if (item.get('NoContent') == 0 or is_bron(domain_data.get('servicetype'))) and len(item.get('linkouturl', '').strip()) > 5:
                            # External link
                            foot += '<li><a style="padding-right: 0px !important;" href="' + item['linkouturl'] + '">' + clean_title(seo_filter_text_custom(item['restitle'])) + '</a>' + newsf + '</li>\n'
                        else:
                            # Internal link
                            slug = seo_slug(item['restitle']) + '-' + str(item['id']) + '/'
                            foot += '<li><a style="padding-right: 0px !important;" href="' + linkdomain + '/' + slug + '">' + clean_title(seo_filter_text_custom(item['restitle'])) + '</a>' + newsf + '</li>\n'
                    else:
                        # Business Collective link only
                        slug = seo_slug(item['restitle']) + '-' + str(item['id']) + 'bc/'
                        foot += '<li><a style="padding-right: 0px !important;" href="' + linkdomain + '/' + slug + '">' + clean_title(seo_filter_text_custom(item['restitle'])) + '</a></li>\n'
                
                num_lnks += 1
        
        foot += '</ul>\n'
        foot += 'Articles</li>\n'
    
    # Add Blog and FAQ links if configured
    if domain_settings.get('blogUrl') and len(domain_settings['blogUrl']) > 10:
        foot += '<li><a class="url" style="width: 100%;font-size:12px;line-height:13px;" target="_blank" href="' + domain_settings['blogUrl'] + '">Blog</a></li>\n'
    
    if domain_settings.get('faqUrl') and len(domain_settings['faqUrl']) > 10:
        foot += '<li><a class="url" style="width: 100%;font-size:12px;line-height:13px;" target="_blank" href="' + domain_settings['faqUrl'] + '">FAQ</a></li>\n'
    
    # Build final footer HTML
    if domain_data.get('wr_name'):
        ltest = domain_data['wr_name']
    else:
        ltest = domain_data['domain_name']
    
    foot += '</ul><a href="' + linkdomain + '/"><div class="seo-button-paid">&copy; ' + str(datetime.now().year) + ' ' + ltest + '</div></a></li></ul>\n'
    
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


def seo_filter_text_custom(text: str) -> str:
    """Clean text similar to PHP seo_filter_text_custom."""
    import re
    text = text.strip()
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
    text = text.strip()
    text = re.sub(r'&(amp;)+', '&', text)
    text = text.replace("&#39;", "'")
    text = text.replace("&#124;", "|")
    text = text.replace(":", "")
    text = text.replace("'", "")
    return text


def to_ascii(text: str) -> str:
    """Convert text to ASCII (simplified version of PHP toAscii)."""
    import html
    import re
    text = seo_filter_text_custom(text)
    text = text.replace(' &#x26;', '')
    text = html.unescape(text)
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


def clean_title(text: str) -> str:
    """Clean title for display (simplified version of seo_automation_clean_title)."""
    text_lower = text.lower()
    if text.strip() == text_lower.strip():
        # Title case
        return text.strip().title()
    else:
        return text.strip()


def is_bron(servicetype: Optional[int]) -> bool:
    """Check if service type is BRON."""
    if not servicetype:
        return False
    sql = "SELECT * FROM bwp_services WHERE servicetype LIKE 'BRON %%' AND servicetype != 'SEOM 5' AND id = %s"
    result = db.fetch_all(sql, (servicetype,))
    return bool(result)

