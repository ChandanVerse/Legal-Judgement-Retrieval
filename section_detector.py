"""
Section detection module for legal judgments
Identifies and extracts structured sections from legal documents
"""
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Section:
    """Represents a detected section in a legal document"""
    section_type: str
    start_pos: int
    end_pos: int
    page_number: Optional[int] = None
    confidence: float = 1.0
    header_text: str = ""

class SectionDetector:
    """Detects and extracts sections from legal judgment text"""

    # Section patterns with multiple variations
    SECTION_PATTERNS = {
        'facts': [
            r'\bFACTS?\s+OF\s+THE\s+CASE\b',
            r'\bFACTS?\b',
            r'\bBACKGROUND\s+FACTS?\b',
            r'\bFACTUAL\s+BACKGROUND\b',
            r'\bBRIEF\s+FACTS?\b',
        ],
        'grounds': [
            r'\bGROUNDS?\b',
            r'\bISSUES?\s+FOR\s+CONSIDERATION\b',
            r'\bISSUES?\s+INVOLVED\b',
            r'\bQUESTIONS?\s+OF\s+LAW\b',
            r'\bQUESTIONS?\s+FOR\s+DETERMINATION\b',
            r'\bPOINTS?\s+FOR\s+DETERMINATION\b',
        ],
        'prayers': [
            r'\bPRAYERS?\b',
            r'\bRELIEFS?\s+SOUGHT\b',
            r'\bRELIEFS?\s+PRAYED\s+FOR\b',
            r'\bRELIEFS?\s+CLAIMED\b',
            r'\bRELIEF\b',
            r'\bREMEDY\s+SOUGHT\b',
        ],
        'arguments_petitioner': [
            r'\bARGUMENTS?\s+OF\s+THE\s+PETITIONER\b',
            r'\bARGUMENTS?\s+OF\s+THE\s+APPELLANT\b',
            r'\bPETITIONER.?S\s+SUBMISSIONS?\b',
            r'\bAPPELLANT.?S\s+SUBMISSIONS?\b',
            r'\bCASE\s+OF\s+THE\s+PETITIONER\b',
        ],
        'arguments_respondent': [
            r'\bARGUMENTS?\s+OF\s+THE\s+RESPONDENT\b',
            r'\bRESPONDENT.?S\s+SUBMISSIONS?\b',
            r'\bCASE\s+OF\s+THE\s+RESPONDENT\b',
            r'\bDEFEN[CS]E\s+SUBMISSIONS?\b',
        ],
        'ratio_decidendi': [
            r'\bRATIO\s+DECIDENDI\b',
            r'\bREASONING\b',
            r'\bDISCUSSION\s+AND\s+ANALYSIS\b',
            r'\bANALYSIS\b',
            r'\bFINDINGS?\b',
            r'\bCONSIDERATION\b',
            r'\bOPINION\s+OF\s+THE\s+COURT\b',
        ],
        'obiter_dicta': [
            r'\bOBITER\s+DICTA\b',
            r'\bOBSERVATIONS?\b',
            r'\bREMARKS?\b',
        ],
        'judgment': [
            r'\bJUDGMENT\b',
            r'\bJUDGEMENT\b',
            r'\bORDER\b',
            r'\bDECISION\b',
            r'\bFINAL\s+ORDER\b',
            r'\bCONCLUSION\b',
            r'\bDISPOSITION\b',
        ],
    }

    def __init__(self):
        """Initialize the section detector"""
        self.compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile all regex patterns for efficiency"""
        compiled = {}
        for section_type, patterns in self.SECTION_PATTERNS.items():
            compiled[section_type] = [
                re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                for pattern in patterns
            ]
        return compiled

    def detect_sections(self, text: str) -> List[Section]:
        """
        Detect all sections in the text

        Args:
            text: Full text of the legal document

        Returns:
            List of Section objects sorted by position
        """
        detected_sections = []

        # Find all section headers
        for section_type, pattern_list in self.compiled_patterns.items():
            for pattern in pattern_list:
                for match in pattern.finditer(text):
                    section = Section(
                        section_type=section_type,
                        start_pos=match.start(),
                        end_pos=-1,  # Will be filled later
                        header_text=match.group(0),
                        confidence=self._calculate_confidence(match, text)
                    )
                    detected_sections.append(section)

        # Sort by position
        detected_sections.sort(key=lambda x: x.start_pos)

        # Set end positions (each section ends where the next begins)
        for i in range(len(detected_sections) - 1):
            detected_sections[i].end_pos = detected_sections[i + 1].start_pos

        # Last section extends to end of document
        if detected_sections:
            detected_sections[-1].end_pos = len(text)

        # Remove duplicates (if multiple patterns matched same section)
        detected_sections = self._remove_duplicate_sections(detected_sections)

        return detected_sections

    def _calculate_confidence(self, match: re.Match, text: str) -> float:
        """
        Calculate confidence score for section detection

        Higher confidence if:
        - Header is on its own line
        - Header is in uppercase
        - Header is followed by a newline
        """
        confidence = 0.7  # Base confidence

        header = match.group(0)
        start = match.start()
        end = match.end()

        # Check if uppercase
        if header.isupper():
            confidence += 0.15

        # Check if on its own line (preceded by newline)
        if start > 0 and text[start - 1] in '\n\r':
            confidence += 0.1

        # Check if followed by newline
        if end < len(text) and text[end] in '\n\r:':
            confidence += 0.05

        return min(confidence, 1.0)

    def _remove_duplicate_sections(self, sections: List[Section]) -> List[Section]:
        """
        Remove duplicate sections that are very close to each other
        Keep the one with higher confidence
        """
        if not sections:
            return sections

        filtered = []
        i = 0

        while i < len(sections):
            current = sections[i]

            # Check if next section is very close (within 100 characters)
            if i + 1 < len(sections):
                next_section = sections[i + 1]
                if (next_section.start_pos - current.start_pos < 100 and
                    next_section.section_type == current.section_type):
                    # Keep the one with higher confidence
                    if next_section.confidence > current.confidence:
                        filtered.append(next_section)
                        i += 2
                    else:
                        filtered.append(current)
                        i += 2
                    continue

            filtered.append(current)
            i += 1

        return filtered

    def extract_section_content(self, text: str, section: Section) -> str:
        """Extract the content of a specific section"""
        content = text[section.start_pos:section.end_pos]

        # Remove the header itself from content
        content = content[len(section.header_text):].strip()

        return content

    def get_section_stats(self, sections: List[Section]) -> Dict[str, int]:
        """Get statistics about detected sections"""
        stats = {}
        for section in sections:
            stats[section.section_type] = stats.get(section.section_type, 0) + 1
        return stats

    def detect_with_fallback(self, text: str) -> List[Section]:
        """
        Detect sections with fallback to generic section if none found

        If no sections are detected, creates a single 'general' section
        """
        sections = self.detect_sections(text)

        if not sections:
            # Create a fallback 'general' section for entire document
            sections = [Section(
                section_type='general',
                start_pos=0,
                end_pos=len(text),
                confidence=0.5,
                header_text='[No sections detected]'
            )]

        return sections
