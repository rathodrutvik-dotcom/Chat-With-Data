"""
Enhanced entity extraction for better metadata tagging and chunk enrichment.

This module extracts structured entities (project names, people, dates, etc.)
from documents to enable better counting, listing, and filtering queries.
"""

import logging
import re
from typing import List, Dict, Set, Optional


def extract_project_names(text: str) -> List[str]:
    """
    Extract project names from text using common patterns.
    
    Looks for patterns like:
    - "Project Name:" or "Project:" followed by text
    - Lines starting with numbers (1., 2., etc.) often list projects
    - Capitalized phrases that look like project titles
    
    Args:
        text: Document text
        
    Returns:
        List of detected project names
    """
    if not text:
        return []
    
    projects = set()
    
    # Pattern 1: "Project Name:" or "Project:" or "Project Title:"
    project_label_pattern = r'(?:Project\s+(?:Name|Title)?|Title)\s*[:\-]\s*([A-Z][A-Za-z0-9\s\-&,]+?)(?:\n|\.|\||$)'
    for match in re.finditer(project_label_pattern, text, re.IGNORECASE):
        project_name = match.group(1).strip()
        # Filter out label-only matches
        if project_name.lower() in ['project name', 'project', 'title']:
            continue
        if len(project_name) > 8 and len(project_name) < 100:  # Reasonable length
            projects.add(project_name)
    
    # Pattern 2: Numbered lists (often project listings)
    # e.g., "1. AI-Powered Document Intelligence Platform"
    numbered_pattern = r'^\s*\d+[\.)]\s+([A-Z][A-Za-z0-9\s\-&,]{8,99})(?:\n|$)'
    for match in re.finditer(numbered_pattern, text, re.MULTILINE):
        project_name = match.group(1).strip()
        # Filter out common non-project patterns and short matches
        if not re.match(r'^(Introduction|Overview|Conclusion|Summary|Background|The|In|On)', project_name):
            # Must contain project-related keywords
            if any(keyword in project_name.lower() for keyword in ['system', 'platform', 'solution', 'management', 'service', 'project']):
                projects.add(project_name)
    
    # Pattern 3: Look for phrases with "Project" or "System" in them (must be title case)
    project_system_pattern = r'\b([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){1,}(?:\s+(?:Project|System|Platform|Solution|Management|Service))\b)'
    for match in re.finditer(project_system_pattern, text):
        project_name = match.group(1).strip()
        if len(project_name) > 12 and len(project_name) < 100:
            projects.add(project_name)
    
    result = sorted(list(projects))  # Sort for consistency
    if result:
        logging.info("Extracted %d project names: %s", len(result), result)
    
    return result


def extract_person_names(text: str) -> List[str]:
    """
    Extract person names from text.
    
    Looks for patterns like:
    - "Name:" followed by a capitalized name
    - Common name patterns (First Last)
    
    Args:
        text: Document text
        
    Returns:
        List of detected person names
    """
    if not text:
        return []
    
    names = set()
    
    # Pattern 1: "Name:" or "Candidate:" or "Person:" followed by name
    name_label_pattern = r'(?:Name|Candidate|Person|Applicant|Individual)\s*[:\-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})'
    for match in re.finditer(name_label_pattern, text, re.IGNORECASE):
        name = match.group(1).strip()
        if len(name) > 4 and len(name) < 50:
            # Filter out project-related terms
            if not any(term in name for term in ['System', 'Project', 'Platform', 'Management', 'Solution']):
                names.add(name)
    
    # Pattern 2: Common name patterns (2-3 capitalized words, conservative)
    # Only match after name-related labels to reduce false positives
    name_context_pattern = r'(?:Name|Candidate|Person|Applicant|Contact|Author|By)\s*[:\-]?\s*([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
    for match in re.finditer(name_context_pattern, text):
        name = match.group(1).strip()
        if len(name) > 5 and len(name) < 50:
            word_count = len(name.split())
            if 2 <= word_count <= 3:
                # Additional filter - no tech terms
                if not any(term in name for term in ['System', 'Project', 'Platform', 'Document', 'Intelligence']):
                    names.add(name)
    
    result = sorted(list(names))
    if result:
        logging.info("Extracted %d person names: %s", len(result), result)
    
    return result


def extract_dates(text: str) -> List[str]:
    """
    Extract dates and timelines from text.
    
    Args:
        text: Document text
        
    Returns:
        List of detected dates/timelines
    """
    if not text:
        return []
    
    dates = set()
    
    # Common date patterns
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY or DD-MM-YYYY
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',  # Month DD, YYYY
        r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',  # DD Month YYYY
        r'\b(?:Q[1-4]|Quarter\s+[1-4])\s+\d{4}\b',  # Q1 2024
        r'\b\d{4}\b',  # Just year
    ]
    
    for pattern in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            dates.add(match.group(0))
    
    # Timeline patterns (e.g., "6 months", "3 years")
    timeline_pattern = r'\b\d+\s+(?:day|week|month|year)s?\b'
    for match in re.finditer(timeline_pattern, text, re.IGNORECASE):
        dates.add(match.group(0))
    
    return list(dates)


def extract_locations(text: str) -> List[str]:
    """
    Extract location names from text.
    
    Args:
        text: Document text
        
    Returns:
        List of detected locations
    """
    if not text:
        return []
    
    locations = set()
    
    # Pattern 1: "Location:" followed by text
    location_label_pattern = r'(?:Location|Place|Site|Address|City|Country)\s*[:\-]\s*([A-Z][A-Za-z0-9\s,\-]+?)(?:\n|\.|\|)'
    for match in re.finditer(location_label_pattern, text, re.IGNORECASE):
        location = match.group(1).strip()
        if len(location) > 3 and len(location) < 100:
            locations.add(location)
    
    # Pattern 2: Common city/country patterns
    location_pattern = r'\b([A-Z][a-z]+(?:,\s+[A-Z][a-z]+)+)\b'
    for match in re.finditer(location_pattern, text):
        location = match.group(1).strip()
        if len(location) > 3 and len(location) < 100:
            locations.add(location)
    
    return list(locations)


def enrich_chunk_metadata(chunk_text: str, document_metadata: Dict) -> Dict:
    """
    Enrich chunk metadata with extracted entities.
    
    This enables better filtering, counting, and listing queries.
    
    Args:
        chunk_text: The chunk's text content
        document_metadata: Existing metadata from the document
        
    Returns:
        Enhanced metadata dictionary
    """
    enhanced_metadata = dict(document_metadata)
    
    # Extract entities from chunk
    projects = extract_project_names(chunk_text)
    persons = extract_person_names(chunk_text)
    dates = extract_dates(chunk_text)
    locations = extract_locations(chunk_text)
    
    # Add to metadata (convert lists to strings for ChromaDB compatibility)
    if projects:
        enhanced_metadata["projects"] = ", ".join(projects)  # Convert list to string
        enhanced_metadata["project_count"] = len(projects)
        enhanced_metadata["contains_projects"] = True
    
    if persons:
        enhanced_metadata["persons"] = ", ".join(persons)  # Convert list to string
        enhanced_metadata["person_count"] = len(persons)
        enhanced_metadata["contains_persons"] = True
    
    if dates:
        enhanced_metadata["dates"] = ", ".join(dates)  # Convert list to string
        enhanced_metadata["date_count"] = len(dates)
        enhanced_metadata["contains_dates"] = True
    
    if locations:
        enhanced_metadata["locations"] = ", ".join(locations)  # Convert list to string
        enhanced_metadata["location_count"] = len(locations)
        enhanced_metadata["contains_locations"] = True
    
    return enhanced_metadata


def inject_entity_prefixes(chunk_text: str, metadata: Dict) -> str:
    """
    Inject entity names as prefixes to chunk content for better retrieval.
    
    This helps when users ask "How many projects?" - the chunks will have
    project names prominently featured.
    
    Args:
        chunk_text: Original chunk text
        metadata: Metadata with extracted entities
        
    Returns:
        Enhanced chunk text with entity prefixes
    """
    prefixes = []
    
    # Add project names (already comma-separated string)
    if metadata.get("projects"):
        project_names = metadata["projects"]
        # Check if it's a reasonable length (not too many projects)
        if len(project_names) < 200:  # Character limit for prefix
            prefixes.append(f"[Projects: {project_names}]")
    
    # Add person names (already comma-separated string)
    if metadata.get("persons"):
        person_names = metadata["persons"]
        if len(person_names) < 100:  # Character limit for prefix
            prefixes.append(f"[Persons: {person_names}]")
    
    # Combine prefixes with original text
    if prefixes:
        prefix_text = " ".join(prefixes)
        return f"{prefix_text}\n\n{chunk_text}"
    
    return chunk_text


__all__ = [
    "extract_project_names",
    "extract_person_names",
    "extract_dates",
    "extract_locations",
    "enrich_chunk_metadata",
    "inject_entity_prefixes",
]
