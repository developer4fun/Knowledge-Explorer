import json
import os
import time
import datetime
import fitz
import re
import argparse
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from collections import Counter

try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

class DocumentAnalyst:
    def __init__(self):
        """
        Initialize the Document Analyst with a robust, universal approach
        """
        self.stopwords = set(stopwords.words('english'))
        self.stopwords.update(['may', 'also', 'many', 'would', 'could', 'one', 'two', 'three', 'four'])
        print("Universal document analyzer initialized")
        
    def extract_sections_from_pdf(self, pdf_path):
        """
        Extract sections and their content from a PDF document using robust detection.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            list: List of dictionaries containing section information
        """
        sections = []
        
        try:
            doc = fitz.open(pdf_path)
            
            potential_titles = []
            for page_num, page in enumerate(doc):
                text = page.get_text()
                lines = text.split('\n')
                
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                    
                    is_isolated = (i == 0 or not lines[i-1].strip()) and (i == len(lines)-1 or not lines[i+1].strip())
                    is_potential_title = (
                        line[0].isupper() and 
                        len(line.split()) <= 8 and 
                        not line.endswith('.') and
                        (is_isolated or line.isupper() or all(word[0].isupper() for word in line.split()))
                    )
                    
                    if is_potential_title:
                        potential_titles.append((line, page_num))
            
            for i, (title, page_num) in enumerate(potential_titles):
                content = []
                current_page = page_num
                next_title_page = potential_titles[i+1][1] if i < len(potential_titles)-1 else None
                next_title = potential_titles[i+1][0] if i < len(potential_titles)-1 else None
                
                page_text = doc[current_page].get_text()
                lines = page_text.split('\n')
                
                title_found = False
                for j, line in enumerate(lines):
                    if line.strip() == title:
                        title_found = True
                        continue
                    
                    if title_found:
                        if next_title and line.strip() == next_title and current_page == next_title_page:
                            break
                        content.append(line.strip())
                
                if next_title_page is not None and next_title_page > current_page:
                    for p in range(current_page + 1, next_title_page + 1):
                        page_text = doc[p].get_text()
                        lines = page_text.split('\n')
                        
                        for line in lines:
                            if p == next_title_page and line.strip() == next_title:
                                break
                            content.append(line.strip())
                
                if content:
                    sections.append({
                        "title": title,
                        "content": " ".join([c for c in content if c]),
                        "page_number": page_num + 1
                    })
            
            doc.close()
            
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            
        return sections
    
    def extract_keywords(self, text):
        """
        Extract important keywords from text.
        
        Args:
            text (str): Text to analyze
            
        Returns:
            list: List of keywords with their frequency
        """
        words = re.findall(r'\b\w+\b', text.lower())
        
        words = [word for word in words if word not in self.stopwords and len(word) > 2]
        
        word_counts = Counter(words)
        
        return word_counts.most_common(20)
    
    def calculate_relevance(self, section, persona, job):
        """
        Calculate section relevance using keyword matching and content analysis.
        
        Args:
            section (dict): Section information including title and content
            persona (str): Persona description
            job (str): Job to be done
            
        Returns:
            float: Relevance score
        """
        title = section["title"]
        content = section["content"]
        
        query = f"{persona} {job}"
        query_keywords = dict(self.extract_keywords(query))
        
        title_keywords = dict(self.extract_keywords(title))
        content_keywords = dict(self.extract_keywords(content))
        
        title_overlap = sum(title_keywords.get(word, 0) for word in query_keywords)
        content_overlap = sum(min(content_keywords.get(word, 0), 5) for word in query_keywords)
        
        content_length = min(len(content.split()), 1000) / 1000.0
        
        unique_words = len(set(word for word in re.findall(r'\b\w+\b', content.lower()) 
                              if word not in self.stopwords and len(word) > 3))
        content_diversity = min(unique_words, 200) / 200.0
        
        relevance_score = (
            (title_overlap * 3.0) +
            (content_overlap * 1.5) +
            (content_length * 1.0) +
            (content_diversity * 1.0)
        )
        
        normalized_score = min(relevance_score / 20.0, 1.0)
        
        return normalized_score
    
    def extract_subsections(self, section_text):
        """
        Extract meaningful subsections using sentence importance scoring.
        
        Args:
            section_text (str): Text content of the section
            
        Returns:
            str: Refined text with key subsections
        """
        sentences = sent_tokenize(section_text)
        
        if len(sentences) <= 5:
            return section_text
        
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            keywords = dict(self.extract_keywords(sentence))
            keyword_count = sum(keywords.values())
            
            position_score = 0
            if i < 3:
                position_score = 1.0 - (i * 0.2)
            elif i >= len(sentences) - 3:
                position_score = 0.6 + ((i - (len(sentences) - 3)) * 0.2)
            
            words = len(sentence.split())
            length_score = min(words / 20.0, 1.0) if words < 50 else 2.0 - (words / 50.0)
            length_score = max(0.0, min(length_score, 1.0))
            
            info_indicators = ['important', 'key', 'significant', 'essential', 'must', 'should', 
                               'recommend', 'popular', 'best', 'top', 'famous']
            indicator_score = 0.5 if any(indicator in sentence.lower() for indicator in info_indicators) else 0
            
            final_score = (keyword_count * 0.4) + (position_score * 0.3) + (length_score * 0.2) + (indicator_score * 0.1)
            
            scored_sentences.append((sentence, final_score))
        
        sorted_sentences = sorted(scored_sentences, key=lambda x: x[1], reverse=True)
        top_sentences = [s[0] for s in sorted_sentences[:5]]
        
        ordered_top_sentences = [s for s in sentences if s in top_sentences]
        
        return " ".join(ordered_top_sentences)
    
    def analyze_documents(self, input_data):
        """
        Analyze documents based on input JSON data.
        
        Args:
            input_data (dict): Input JSON data with documents, persona, and job
            
        Returns:
            dict: Output JSON with analysis results
        """
        start_time = time.time()
        
        documents = input_data.get("documents", [])
        persona_info = input_data.get("persona", {})
        job_info = input_data.get("job_to_be_done", {})
        
        persona = persona_info.get("role", "")
        job = job_info.get("task", "")
        
        output = {
            "metadata": {
                "input_documents": [doc.get("filename", "") for doc in documents],
                "persona": persona,
                "job_to_be_done": job,
                "processing_timestamp": datetime.datetime.now().isoformat()
            },
            "extracted_sections": [],
            "subsection_analysis": []
        }
        
        all_sections = []
        
        for doc in documents:
            filename = doc.get("filename", "")
            pdf_path = os.path.join("PDFs", filename)
            if not os.path.exists(pdf_path):
                print(f"Warning: File {pdf_path} not found. Skipping.")
                continue
                
            print(f"Processing document: {pdf_path}")
            sections = self.extract_sections_from_pdf(pdf_path)
            
            for section in sections:
                section["document"] = filename
                section["relevance"] = self.calculate_relevance(section, persona, job)
                all_sections.append(section)
        
        all_sections.sort(key=lambda x: x["relevance"], reverse=True)
        top_sections = all_sections[:5]
        
        for i, section in enumerate(top_sections):
            output["extracted_sections"].append({
                "document": section["document"],
                "section_title": section["title"],
                "importance_rank": i + 1,
                "page_number": section["page_number"]
            })
            
            refined_text = self.extract_subsections(section["content"])
            output["subsection_analysis"].append({
                "document": section["document"],
                "refined_text": refined_text,
                "page_number": section["page_number"]
            })
        
        elapsed_time = time.time() - start_time
        print(f"Analysis completed in {elapsed_time:.2f} seconds")
        
        return output