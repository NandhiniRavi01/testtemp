from flask import Flask, Blueprint, request, jsonify
import pandas as pd
import re
import dns.resolver
import io
from typing import List, Dict, Optional
import tldextract
from ddgs import DDGS
import time
import requests

# Create blueprint
file_processor_bp = Blueprint('file_processor', __name__)

class CompanyEmailProcessor:
    def __init__(self):
        self.common_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
        self.known_company_domains = {
            # Your existing domain mappings...
            'microsoft': 'microsoft.com',
            'google': 'google.com',
            'apple': 'apple.com',
            'amazon': 'amazon.com',
            'meta': 'meta.com',
            'facebook': 'facebook.com',
            'twitter': 'twitter.com',
            'linkedin': 'linkedin.com',
            'netflix': 'netflix.com',
            'spotify': 'spotify.com',
            'uber': 'uber.com',
            'airbnb': 'airbnb.com',
            'salesforce': 'salesforce.com',
            'adobe': 'adobe.com',
            'intel': 'intel.com',
            'ibm': 'ibm.com',
            'oracle': 'oracle.com',
            'cisco': 'cisco.com',
            'dell': 'dell.com',
            'hp': 'hp.com',
            'phonepe': 'phonepe.com',
            'ola': 'olacabs.com',
            'infosys': 'infosys.com',
            'tcs': 'tcs.com',
            'wipro': 'wipro.com',
            'hcl': 'hcl.com',
            'accenture': 'accenture.com',
            'capgemini': 'capgemini.com',
            'cognizant': 'cognizant.com',
            'uae': 'uae.gov.ae',
            'g42': 'g42.ai',
            'openai': 'openai.com',
            'cerebras': 'cerebras.ai',
            'european commission': 'ec.europa.eu',
            'canada': 'canada.ca',
            'cohesity': 'cohesity.com',
            'dubai chambers': 'dubaichambers.com',
            'tenstorrent': 'tenstorrent.com',
            'paradromics': 'paradromics.com',
            'phison': 'phison.com',
            'kwf capital': 'kwfcapital.com',
            'siemens': 'siemens.com',
            'soundcloud': 'soundcloud.com',
            'dubai future': 'dubaifuture.ae',
            'slovenia': 'gov.si',
            'united nations': 'un.org',
            'liquid ai': 'liquid.ai',
            'aws': 'aws.amazon.com',
            'türkiye': 'gov.tr',
            'mammoth biosciences': 'mammoth.bio',
            'm42': 'm42.ae',
            'octopus energy': 'octopus.energy',
            'lebanon': 'gov.lb',
            'sandboxaq': 'sandboxaq.com',
            'ibm': 'ibm.com',
            'skeleton technologies': 'skeletontech.com',
            'technology innovation institute': 'tii.ae',
            'amd': 'amd.com',
            'etihad rail': 'etihadrail.ae',
            'pakistan': 'gov.pk',
            'trendyol': 'trendyol.com',
            'vertiv': 'vertiv.com',
            'quantum basel': 'quantumbasel.com',
            'brasil': 'gov.br',
            'china energy': 'cesi.cn',
            'oleary ventures': 'olearyventures.com',
            'oecd': 'oecd.org',
            'unido': 'unido.org',
            'digital dubai': 'digitaldubai.ae',
            'dominos': 'dominos.com',
            'fluidstack': 'fluidstack.io',
            'sanofi': 'sanofi.com',
            'solutions by stc': 'stc.sa',
            'huawei': 'huawei.com',
            'ai71': 'ai71.ai',
            'microsoft': 'microsoft.com',
            'snowflake': 'snowflake.com',
            'bureau of indian standards': 'bis.gov.in',
            'dreamers and doers': 'dreamersandoers.com', 
            'mwt informatics': 'mwtinformatics.com',
            'kovai': 'kovai.co',
            'arali ventures': 'araliventures.com',
            'inflection point ventures': 'ipv.com',
            'hub.brussels': 'hub.brussels',
            'thedicof': 'dicof.org',
            'iamneo': 'iamneo.ai',
            'agrizen': 'agrizen.com',
            'droolls': 'droolls.com',
            'arai-amtif': 'araiindia.com',
            'oysterable': 'oysterable.com',
            'tnwesafe': 'tnwesafe.in',
            
            # Government patterns
            'minister': 'gov.au',
            'department': 'gov.au',
            'ministry': 'gov.au',
            'republic': 'gov.au',
        }
        self.domain_cache = {}
        self.failed_lookups = set()
        self.verifier_api_url = "https://rapid-email-verifier.fly.dev/api/validate/batch"

    def extract_company_name(self, text: str) -> Optional[str]:
        """Extract company name from text using pattern matching"""
        if not text or not isinstance(text, str):
            return None
            
        patterns = [
            r'\b([A-Z][a-zA-Z&]+)\s+(Inc|Corp|Corporation|Company|Co|LLC|Ltd|Limited)\b',
            r'\b([A-Z][a-zA-Z&]+\s+[A-Z][a-zA-Z]+)\s+(Technologies|Tech|Solutions|Systems|Software|Consulting)\b',
            r'\b[A-Z][a-zA-Z]+\s+(International|Global|Enterprises|Group)\b',
            r'\b([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        if len(words) >= 2:
            return ' '.join(words[:2])
        
        return None

    def _clean_company_name(self, company_name: str) -> str:
        """Clean company name for domain generation"""
        if not company_name:
            return ""
        
        clean_name = re.sub(
            r'\s+(Inc|Corp|Corporation|Company|Co|LLC|Ltd|Limited|Technologies|Tech|Solutions|Systems|Software|Consulting|International|Global|Enterprises|Group|Pvt|Private)$', 
            '', company_name, flags=re.IGNORECASE
        ).strip()
        
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', clean_name)
        clean_name = re.sub(r'\s+', ' ', clean_name)
        
        return clean_name

    def find_company_domain(self, company_name: str) -> Optional[str]:
        """Find company domain using smart strategies with fallback"""
        if not company_name:
            return None
        
        cache_key = company_name.lower().strip()
        if cache_key in self.domain_cache:
            return self.domain_cache[cache_key]
        if cache_key in self.failed_lookups:
            return None
        
        start_time = time.time()
        clean_name = self._clean_company_name(company_name)
        
        known_domain = self._check_known_companies(clean_name)
        if known_domain:
            self.domain_cache[cache_key] = known_domain
            elapsed = time.time() - start_time
            print(f"✅ Domain found via database: {known_domain} ({company_name}) - {elapsed:.3f}s")
            return known_domain
        
        guessed_domain = self._guess_domain_patterns(clean_name)
        if guessed_domain and not self._is_generic_domain(guessed_domain):
            self.domain_cache[cache_key] = guessed_domain
            elapsed = time.time() - start_time
            print(f"✅ Domain found via pattern: {guessed_domain} ({company_name}) - {elapsed:.3f}s")
            return guessed_domain
        
        searched_domain = self._search_domain_fallback(clean_name)
        if searched_domain and not self._is_generic_domain(searched_domain):
            self.domain_cache[cache_key] = searched_domain
            elapsed = time.time() - start_time
            print(f"✅ Domain found via search: {searched_domain} ({company_name}) - {elapsed:.3f}s")
            return searched_domain
        
        self.failed_lookups.add(cache_key)
        elapsed = time.time() - start_time
        print(f"❌ Domain not found: {company_name} - {elapsed:.3f}s")
        return None
    
    def _check_known_companies(self, company_name: str) -> Optional[str]:
        """Check against known company domains"""
        company_lower = company_name.lower()
        
        if company_lower in self.known_company_domains:
            return self.known_company_domains[company_lower]
        
        for known_company, domain in self.known_company_domains.items():
            if known_company in company_lower:
                return domain
        
        return None
    
    def _is_generic_domain(self, domain: str) -> bool:
        """Check if domain is too generic to be a specific company"""
        generic_domains = {
            'office.com', 'company.com', 'business.com', 'corporation.com',
            'enterprise.com', 'organization.com', 'group.com', 'holdings.com',
            'ventures.com', 'partners.com', 'solutions.com', 'technologies.com',
            'systems.com', 'services.com', 'consulting.com', 'international.com',
            'global.com', 'worldwide.com', 'digital.com', 'online.com',
            'network.com', 'platform.com', 'software.com', 'app.com', 'cloud.com',
            'inc.com', 'ltd.com', 'co.com', 'corp.com'
        }
        
        domain_name = domain.lower().split('.')[0]
        
        if domain in generic_domains:
            return True
        
        generic_names = [
            'office', 'company', 'business', 'corporation', 'enterprise',
            'organization', 'group', 'holdings', 'ventures', 'partners',
            'solutions', 'technologies', 'systems', 'services', 'consulting',
            'international', 'global', 'worldwide', 'digital', 'online',
            'network', 'platform', 'software', 'app', 'apps', 'cloud',
            'inc', 'ltd', 'co', 'corp'
        ]
        
        return domain_name in generic_names

    def _guess_domain_patterns(self, company_name: str) -> Optional[str]:
        """Try patterns with HTTP verification"""
        words = company_name.split()
        if not words:
            return None
        
        patterns = self._generate_domain_patterns(words)
        tld_priority = self._get_tld_priority(company_name)
        
        for pattern in patterns:
            for tld in tld_priority:
                domain = pattern + tld
                if self._test_domain_quick_http(domain):
                    return domain
        
        return None

    def _get_tld_priority(self, company_name: str) -> List[str]:
        """Get TLD priority based on company type"""
        company_lower = company_name.lower()
        
        if any(word in company_lower for word in ['ai', 'tech', 'software', 'digital', 'data']):
            return ['.ai', '.com', '.io', '.tech', '.org']
        elif any(word in company_lower for word in ['venture', 'capital', 'fund', 'invest']):
            return ['.vc', '.com', '.capital', '.io']
        elif any(word in company_lower for word in ['government', 'ministry', 'department', 'agency']):
            return ['.gov', '.org', '.com']
        else:
            return ['.com', '.org', '.net', '.io', '.ai', '.co']

    def _generate_domain_patterns(self, words: List[str]) -> List[str]:
        """Generate smart domain patterns"""
        patterns = []
        
        if len(words) == 1:
            company_word = words[0].lower()
            patterns = [
                company_word,
                company_word + 'tech',
                company_word + 'ai',
                company_word + 'systems',
                'get' + company_word,
            ]
        elif len(words) == 2:
            first_word = words[0].lower()
            second_word = words[1].lower()
            patterns = [
                first_word + second_word,
                first_word,
                second_word,
                first_word + '-' + second_word,
                first_word[0] + second_word,
            ]
        else:
            first_word = words[0].lower()
            last_word = words[-1].lower()
            acronym = ''.join([word[0].lower() for word in words if len(word) > 1])
            key_words = [w.lower() for w in words if len(w) > 3 and w.lower() not in ['the', 'and', 'for', 'with']]
            
            patterns = [
                first_word + last_word,
                first_word,
                last_word,
                acronym,
                first_word + acronym,
            ]
            
            if len(key_words) >= 2:
                patterns.append(key_words[0] + key_words[-1])
            if len(key_words) >= 1:
                patterns.append(key_words[0])
        
        patterns = [p for p in set(patterns) if len(p) > 2]
        return patterns[:8]

    def _test_domain_quick_http(self, domain: str) -> bool:
        """Quick HTTP check - like browser testing if domain works"""
        import socket
        
        try:
            socket.setdefaulttimeout(2)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((domain, 80))
            sock.close()
            return result == 0
        except:
            return False

    def _search_domain_fallback(self, company_name: str, timeout_seconds: int = 5) -> Optional[str]:
        """Search domain as fallback with timeout protection"""
        start_time = time.time()
        
        try:
            with DDGS() as ddgs:
                query = f'"{company_name}" website'
                results = list(ddgs.text(query, max_results=2))
                
                for result in results:
                    if time.time() - start_time > timeout_seconds:
                        break
                    
                    url = result.get("href", "")
                    if url:
                        ext = tldextract.extract(url)
                        if ext.domain and ext.suffix:
                            domain = f"{ext.domain}.{ext.suffix}".lower()
                            if self._is_likely_company_domain(company_name, domain):
                                return domain
        except Exception as e:
            print(f"⚠️ Search fallback error for {company_name}: {e}")
        
        return None
    
    def _is_likely_company_domain(self, company_name: str, domain: str) -> bool:
        """Quick validation if domain likely belongs to company"""
        if not company_name or not domain:
            return False
        
        company_clean = re.sub(r'[^a-zA-Z0-9]', '', company_name).lower()
        domain_clean = re.sub(r'\.(com|org|net|co|io|ai|in)$', '', domain.lower())
        
        if company_clean in domain_clean or domain_clean in company_clean:
            return True
        
        company_words = [word.lower() for word in company_name.split() if len(word) > 3]
        for word in company_words:
            if word in domain_clean and len(word) > 3:
                return True
        
        return False
    
    def extract_names_from_text(self, text: str) -> Dict[str, str]:
        """Extract first and last name from various name formats"""
        if not text or not isinstance(text, str):
            return {'first_name': '', 'last_name': ''}
        
        # Clean the text - remove titles and honorifics
        text = text.strip()
        text = re.sub(r'^(H\.E\.|Dr\.|Prof\.|Mr\.|Ms\.|Mrs\.)\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^(THE HON\.|Dato\')\s*', '', text, flags=re.IGNORECASE)
        
        name_patterns = [
            r'^(\w+)\s+(\w+)$',
            r'^(\w+),\s*(\w+)$',
            r'^(\w+)\s+\w\.\s*(\w+)$',
            r'^(\w+)\s+(\w+)\s+\w+$',
        ]
        
        for pattern in name_patterns:
            match = re.match(pattern, text)
            if match:
                if ',' in text:
                    return {'first_name': match.group(2), 'last_name': match.group(1)}
                else:
                    return {'first_name': match.group(1), 'last_name': match.group(2)}
        
        # Handle complex names with multiple parts
        parts = text.split()
        if len(parts) >= 2:
            # Take first part as first name, last part as last name
            return {'first_name': parts[0], 'last_name': parts[-1]}
        elif len(parts) == 1:
            return {'first_name': parts[0], 'last_name': ''}
        
        return {'first_name': '', 'last_name': ''}
    
    def generate_email_patterns(self, first_name: str, last_name: str, domain: str) -> List[str]:
        """Generate common email patterns"""
        if not domain:
            return []
        
        first_name = first_name.lower().strip() if first_name else ''
        last_name = last_name.lower().strip() if last_name else ''
        
        # Clean names - remove special characters and spaces
        first_name_clean = re.sub(r'[^a-zA-Z]', '', first_name)
        last_name_clean = re.sub(r'[^a-zA-Z]', '', last_name)
        
        patterns = []
        
        if first_name_clean and last_name_clean:
            first_initial = first_name_clean[0] if first_name_clean else ''
            last_initial = last_name_clean[0] if last_name_clean else ''
            
            patterns = [
                f"{first_name_clean}.{last_name_clean}@{domain}",
                f"{first_name_clean}{last_name_clean}@{domain}",
                f"{first_initial}{last_name_clean}@{domain}",
                f"{first_name_clean}{last_initial}@{domain}",
                f"{first_name_clean}@{domain}",
                f"{first_initial}.{last_name_clean}@{domain}",
                f"{last_name_clean}.{first_name_clean}@{domain}",
                f"{last_name_clean}{first_name_clean}@{domain}",
                f"{last_name_clean}@{domain}"
            ]
        elif first_name_clean:
            patterns = [f"{first_name_clean}@{domain}"]
        elif last_name_clean:
            patterns = [f"{last_name_clean}@{domain}"]
        else:
            return []
        
        # Remove duplicates and invalid patterns
        valid_patterns = []
        for pattern in patterns:
            if '@' in pattern and len(pattern.split('@')[0]) > 0:
                valid_patterns.append(pattern)
        
        return list(set(valid_patterns))
    
    def _verify_emails_batch(self, emails: List[str]) -> Dict[str, Dict]:
        """Verify multiple emails using Rapid Email Verifier batch API - FIXED VERSION"""
        if not emails:
            return {}
            
        try:
            print(f"🔍 Validating {len(emails)} emails via API...")
            
            response = requests.post(
                self.verifier_api_url,
                json={"emails": emails},
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                api_response = response.json()
                # The API returns {"results": [array of email objects]}
                results_array = api_response.get('results', [])
                
                # Convert array to dictionary keyed by email for easy lookup
                results_dict = {}
                for result in results_array:
                    email = result.get('email')
                    if email:
                        results_dict[email] = result
                
                print(f"✅ API validation completed for {len(results_dict)} emails")
                return results_dict
            else:
                print(f"⚠️ API returned status {response.status_code}: {response.text}")
                return {}
                
        except requests.exceptions.Timeout:
            print(f"⚠️ API timeout for batch verification")
            return {}
        except requests.exceptions.RequestException as e:
            print(f"⚠️ API error for batch verification: {e}")
            return {}
        except Exception as e:
            print(f"⚠️ Unexpected API error for batch verification: {e}")
            return {}

    def validate_emails_with_scores(self, emails: List[str]) -> List[Dict]:
        """Validate multiple emails using Rapid Email Verifier API"""
        if not emails:
            return []
        
        # Use batch API
        batch_results = self._verify_emails_batch(emails)
        
        validation_results = []
        for email in emails:
            result = {
                'email': email,
                'is_valid': False,
                'score': 0,
                'dns_valid': False,
                'score_breakdown': {
                    'api_verification': 0
                },
                'details': {}
            }
            
            # Find this email in batch results
            email_result = batch_results.get(email, {})
            if email_result:
                validations = email_result.get('validations', {})
                score = email_result.get('score', 0)
                status = email_result.get('status', 'INVALID')
                
                # Consider email valid if status is VALID and score is reasonable
                result['is_valid'] = status == 'VALID' and score >= 50
                result['score'] = score
                result['dns_valid'] = validations.get('mx_records', False) and validations.get('domain_exists', False)
                result['score_breakdown']['api_verification'] = score
                result['details']['api_result'] = email_result
                result['details']['validations'] = validations
                result['details']['status'] = status
                
                if result['is_valid']:
                    print(f"   ✅ Valid: {email} (score: {score})")
                else:
                    print(f"   ❌ Invalid: {email} (status: {status}, score: {score})")
            else:
                print(f"   ⚠️ No API result for: {email}")
                # If no API result, do basic validation
                if '@' in email and '.' in email.split('@')[1]:
                    result['is_valid'] = True  # Basic format check
                    result['score'] = 30  # Low score for unverified emails
                    result['score_breakdown']['api_verification'] = 0
                    result['details']['note'] = 'Basic format validation only'
            
            validation_results.append(result)
        
        return validation_results

class FileProcessor:
    def __init__(self):
        self.email_processor = CompanyEmailProcessor()
    
    def process_csv(self, file_content: str) -> List[Dict]:
        """Process CSV file and add email IDs with scores"""
        try:
            df = pd.read_csv(io.StringIO(file_content))
            return self._process_dataframe(df)
        except Exception as e:
            raise Exception(f"Error processing CSV: {str(e)}")
    
    def process_excel(self, file_content: bytes) -> List[Dict]:
        """Process Excel file and add email IDs with scores"""
        try:
            df = pd.read_excel(io.BytesIO(file_content))
            return self._process_dataframe(df)
        except Exception as e:
            raise Exception(f"Error processing Excel file: {str(e)}")
    
    def process_text_file(self, file_content: str) -> List[Dict]:
        """Process text file - each line should contain name and company info"""
        try:
            lines = file_content.split('\n')
            results = []
            
            for line_num, line in enumerate(lines, 1):
                if line.strip():
                    result = self._process_single_record(line.strip(), line_num)
                    results.append(result)
            
            return results
        except Exception as e:
            raise Exception(f"Error processing text file: {str(e)}")
    
    def _process_single_record(self, text: str, line_num: int) -> Dict:
        """Process a single text record and add email IDs with scores"""
        company_name = self.email_processor.extract_company_name(text)
        domain = self.email_processor.find_company_domain(company_name) if company_name else None
        
        names = self.email_processor.extract_names_from_text(text)
        first_name = names['first_name']
        last_name = names['last_name']
        
        generated_emails = []
        valid_emails_with_scores = []
        validation_results = []
        
        print(f"🔍 Processing: {text}")
        print(f"   Company: {company_name}, Domain: {domain}")
        print(f"   Name: {first_name} {last_name}")
        
        if domain and (first_name or last_name):
            generated_emails = self.email_processor.generate_email_patterns(first_name, last_name, domain)
            print(f"   Generated {len(generated_emails)} emails: {generated_emails}")
            
            if generated_emails:
                # Validate emails
                batch_validations = self.email_processor.validate_emails_with_scores(generated_emails)
                validation_results = batch_validations
                
                for validation in batch_validations:
                    if validation['is_valid']:
                        valid_emails_with_scores.append({
                            'email': validation['email'],
                            'score': validation['score'],
                            'score_breakdown': validation['score_breakdown'],
                            'dns_valid': validation['dns_valid'],
                            'api_details': validation.get('details', {}).get('api_result', {})
                        })
        
        valid_emails_with_scores.sort(key=lambda x: x['score'], reverse=True)
        
        result = {
            'line_number': line_num,
            'original_text': text,
            'first_name': first_name,
            'last_name': last_name,
            'company_name': company_name,
            'domain': domain,
            'generated_emails': generated_emails,
            'valid_emails_with_scores': valid_emails_with_scores,
            'validation_results': validation_results,
            'best_email': valid_emails_with_scores[0] if valid_emails_with_scores else None
        }
        
        print(f"   Result: {len(valid_emails_with_scores)} valid emails")
        return result
    
    def _process_dataframe(self, df: pd.DataFrame) -> List[Dict]:
        """Process pandas DataFrame and add email IDs with scores"""
        results = []
        
        # Collect all emails for batch processing
        all_emails_to_validate = []
        record_emails_map = {}  # Map record index to its emails
        
        # First pass: collect all data and generate emails
        for index, row in df.iterrows():
            result = self._create_initial_result(row, index)
            
            # Generate emails if we have names and domain
            if (result['first_name'] or result['last_name']) and result['domain']:
                emails = self.email_processor.generate_email_patterns(
                    result['first_name'], 
                    result['last_name'], 
                    result['domain']
                )
                result['generated_emails'] = emails
                
                # Store for batch validation
                record_emails_map[index] = emails
                all_emails_to_validate.extend(emails)
            
            results.append(result)
        
        # Batch validate all emails
        if all_emails_to_validate:
            print(f"🔄 Batch validating {len(all_emails_to_validate)} emails...")
            batch_validations = self.email_processor.validate_emails_with_scores(all_emails_to_validate)
            
            # Create email to validation map
            email_validation_map = {v['email']: v for v in batch_validations}
            
            # Second pass: assign validation results to respective records
            for index, result in enumerate(results):
                valid_emails_with_scores = []
                validation_results = []
                
                emails = record_emails_map.get(index, [])
                for email in emails:
                    validation = email_validation_map.get(email, {})
                    if validation:
                        validation_results.append(validation)
                        if validation.get('is_valid', False):
                            valid_emails_with_scores.append({
                                'email': email,
                                'score': validation['score'],
                                'score_breakdown': validation['score_breakdown'],
                                'dns_valid': validation['dns_valid'],
                                'api_details': validation.get('details', {}).get('api_result', {})
                            })
                
                # Sort by score and update result
                valid_emails_with_scores.sort(key=lambda x: x['score'], reverse=True)
                result['valid_emails_with_scores'] = valid_emails_with_scores
                result['validation_results'] = validation_results
                result['best_email'] = valid_emails_with_scores[0] if valid_emails_with_scores else None
        
        return results
    
    def _create_initial_result(self, row, index: int) -> Dict:
        """Create initial result structure from dataframe row"""
        result = {
            'row_number': index + 1,
            'first_name': '',
            'last_name': '',
            'full_name': '',
            'company_name': '',
            'domain': '',
            'generated_emails': [],
            'valid_emails_with_scores': [],
            'validation_results': [],
            'best_email': None,
            'original_data': {}
        }
        
        # Extract name and company from various column patterns
        name_text = ''
        company_text = ''
        
        # Store all original data
        for col in row.index:
            value = str(row[col]) if pd.notna(row[col]) else ''
            result['original_data'][col] = value
            
            col_lower = col.lower()
            
            # Check for name columns
            if any(name_keyword in col_lower for name_keyword in ['name', 'fullname', 'person', 'contact', 'employee']):
                if value and not name_text:
                    name_text = value
                    result['full_name'] = value
            
            # Check for company columns  
            elif any(company_keyword in col_lower for company_keyword in ['company', 'org', 'organization', 'firm', 'business']):
                if value and not company_text:
                    company_text = value
                    result['company_name'] = value
        
        # If no specific company column found, try to extract from any column
        if not company_text:
            for col in row.index:
                if pd.notna(row[col]):
                    value = str(row[col])
                    potential_company = self.email_processor.extract_company_name(value)
                    if potential_company:
                        company_text = potential_company
                        result['company_name'] = potential_company
                        break
        
        # Extract names from name text
        if name_text:
            names = self.email_processor.extract_names_from_text(name_text)
            result['first_name'] = names['first_name']
            result['last_name'] = names['last_name']
        
        # Find domain
        if result['company_name']:
            result['domain'] = self.email_processor.find_company_domain(result['company_name'])
        
        return result

# Initialize processor
file_processor = FileProcessor()

# Routes remain the same...
@file_processor_bp.route('/')
def api_home():
    return jsonify({
        'status': 'success', 
        'message': 'Email Generator API is running!',
        'endpoints': {
            'test': 'GET /api/test',
            'upload_file': 'POST /api/upload-file'
        }
    })

@file_processor_bp.route('/test', methods=['GET'])
def test_connection():
    return jsonify({'status': 'success', 'message': 'Backend is working!'})

@file_processor_bp.route('/upload-file', methods=['POST'])
def upload_file():
    """Handle file upload and return data with generated email IDs and scores"""
    start_time = time.time()
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        print(f"✅ Processing file: {file.filename}")
        
        filename = file.filename.lower()
        file_content = file.read()
        
        process_start = time.time()
        
        if filename.endswith('.csv'):
            results = file_processor.process_csv(file_content.decode('utf-8'))
        elif filename.endswith(('.xlsx', '.xls')):
            results = file_processor.process_excel(file_content)
        elif filename.endswith('.txt'):
            results = file_processor.process_text_file(file_content.decode('utf-8'))
        else:
            return jsonify({'error': 'Unsupported file type. Use CSV, Excel, or TXT'}), 400
        
        process_time = time.time() - process_start
        
        # Generate summary
        total_records = len(results)
        total_valid_emails = sum(len(r.get('valid_emails_with_scores', [])) for r in results)
        domains_found = sum(1 for r in results if r.get('domain'))
        emails_generated = sum(len(r.get('generated_emails', [])) for r in results)
        
        response = {
            'status': 'success',
            'file_name': file.filename,
            'total_records_processed': total_records,
            'processing_time_seconds': round(process_time, 2),
            'summary': {
                'valid_emails_found': total_valid_emails,
                'emails_generated': emails_generated,
                'domains_found': domains_found,
                'success_rate': f"{(domains_found/total_records)*100:.1f}%" if total_records > 0 else "0%",
                'email_success_rate': f"{(total_valid_emails/emails_generated)*100:.1f}%" if emails_generated > 0 else "0%"
            },
            'results': results
        }
        
        total_time = time.time() - start_time
        print(f"✅ Total request time: {total_time:.2f} seconds")
        print(f"📊 Summary: {total_valid_emails} valid emails found from {emails_generated} generated")
        
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return jsonify({'error': str(e)}), 500

# def create_app():
#     app = Flask(__name__)
#     app.register_blueprint(file_processor_bp, url_prefix='/api')
    
#     @app.after_request
#     def after_request(response):
#         response.headers.add('Access-Control-Allow-Origin', '*')
#         response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
#         response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
#         return response
    
#     return app

# if __name__ == "__main__":
#     app = create_app()
#     print("🚀 Starting Flask server...")
#     app.run(debug=True, host='0.0.0.0', port=5000)
