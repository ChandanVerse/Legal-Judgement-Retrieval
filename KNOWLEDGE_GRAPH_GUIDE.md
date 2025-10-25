# Knowledge Graph Integration Guide for Legal Judgement Retrieval

## Why Add a Knowledge Graph?

A knowledge graph database will **significantly enhance** your Legal Judgement Retrieval system by:

### 1. Capturing Legal Citation Networks
- Cases cite previous judgments (precedents)
- Build citation chains to understand legal evolution
- Find related cases through citation relationships

### 2. Entity Relationship Modeling
- **Entities**: Judges, Lawyers, Courts, Legal Principles, Statutes, Acts, Parties
- **Relationships**:
  - `Judge -> PRESIDED_OVER -> Case`
  - `Case -> CITES -> Case`
  - `Case -> APPLIES -> LegalPrinciple`
  - `Case -> HEARD_IN -> Court`
  - `Lawyer -> ARGUED_FOR -> Party`

### 3. Document Structure Relationships
You already have section detection! Knowledge graphs can model:
- Facts → Grounds → Arguments → Ratio → Judgment (case flow)
- Section dependencies and references
- Cross-document section similarities

### 4. Hierarchical Court System
- Supreme Court → High Court → District Court
- Model jurisdiction and appeal chains
- Track case progression through courts

### 5. Hybrid Retrieval (Vector + Graph = Better Results!)
- **Vector Search**: Find semantically similar cases
- **Graph Traversal**: Find related cases through citations/precedents
- **Hybrid Scoring**: Combine both for superior ranking

---

## Recommended Knowledge Graph Databases

### 1. Neo4j (Recommended)

**Why Neo4j?**
- Industry standard, battle-tested
- Excellent for legal citation networks
- Cypher query language is intuitive
- Has built-in vector index support for hybrid search!
- Great visualization tools
- Strong community and documentation

**Neo4j AuraDB** (Cloud):
- Serverless option available
- Free tier: 200k nodes, 400k relationships
- Production-ready with automatic scaling

**Neo4j Community Edition** (Self-hosted):
- Free and open source
- Full feature set
- Can run locally or on your servers

### 2. Amazon Neptune

**Why Neptune?**
- Fully managed by AWS
- Serverless option available
- Supports both Property Graph and RDF
- Good for AWS-integrated workflows

**Limitations**:
- More expensive than alternatives
- Vendor lock-in

### 3. ArangoDB

**Why ArangoDB?**
- Multi-model: Graph + Document + Key-Value
- Good performance
- Flexible query language (AQL)

**Limitations**:
- Smaller community than Neo4j
- Less legal-specific tooling

---

## Proposed Hybrid Architecture

```
┌─────────────────┐         ┌─────────────────┐
│   Pinecone      │         │     Neo4j       │
│  (Vector DB)    │         │ (Knowledge Graph│
└────────┬────────┘         └────────┬────────┘
         │                           │
         │   Semantic Search         │   Relationship
         │   (embeddings)            │   Traversal
         │                           │
         └───────────┬───────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  Hybrid Query Engine  │
         │  - Vector similarity  │
         │  - Graph relevance    │
         │  - Combined scoring   │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   Re-ranked Results   │
         └───────────────────────┘
```

---

## Implementation Plan

### Phase 1: Setup Neo4j (Week 1)

1. **Install Neo4j**
   ```bash
   # Option A: Docker (Recommended for local dev)
   docker run \
       --name neo4j \
       -p 7474:7474 -p 7687:7687 \
       -e NEO4J_AUTH=neo4j/your-password \
       neo4j:latest

   # Option B: Cloud (Neo4j AuraDB)
   # Sign up at: https://neo4j.com/cloud/aura/
   ```

2. **Install Python Driver**
   ```bash
   pip install neo4j
   ```

3. **Add to .env**
   ```bash
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your-password
   ```

### Phase 2: Define Graph Schema (Week 1)

#### Node Types

1. **Case Node**
   ```cypher
   (:Case {
     case_id: "UUID",
     title: "Petitioner vs Respondent",
     year: 2024,
     court: "Supreme Court",
     citation: "2024 SCC 123",
     filename: "case.pdf",
     judgment_date: "2024-01-15"
   })
   ```

2. **Section Node**
   ```cypher
   (:Section {
     section_id: "UUID",
     section_type: "facts|grounds|arguments_petitioner|...",
     content: "section text",
     confidence: 0.95,
     vector_id: "pinecone-vector-id"  // Link to Pinecone
   })
   ```

3. **Entity Nodes**
   ```cypher
   (:Judge {name: "Justice X", tenure: "..."})
   (:Court {name: "Supreme Court", jurisdiction: "..."})
   (:LegalPrinciple {name: "Res Judicata", description: "..."})
   (:Statute {name: "IPC Section 302", description: "..."})
   (:Party {name: "Petitioner Name", type: "petitioner|respondent"})
   ```

#### Relationship Types

```cypher
// Case relationships
(case1:Case)-[:CITES]->(case2:Case)
(case1:Case)-[:OVERRULES]->(case2:Case)
(case1:Case)-[:FOLLOWS]->(case2:Case)
(case:Case)-[:HEARD_IN]->(court:Court)
(case:Case)-[:DECIDED_BY]->(judge:Judge)

// Section relationships
(case:Case)-[:HAS_SECTION]->(section:Section)
(section1:Section)-[:REFERENCES]->(section2:Section)
(section:Section)-[:CITES_CASE]->(case:Case)

// Entity relationships
(case:Case)-[:APPLIES]->(principle:LegalPrinciple)
(case:Case)-[:INTERPRETS]->(statute:Statute)
(party:Party)-[:PARTY_TO]->(case:Case)
```

### Phase 3: Build Graph Loader (Week 2)

Create `graphdb.py`:

```python
from neo4j import GraphDatabase
import os

class KnowledgeGraph:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )

    def add_case(self, case_data):
        """Add a case node to the graph"""
        with self.driver.session() as session:
            session.run("""
                CREATE (c:Case {
                    case_id: $case_id,
                    title: $title,
                    year: $year,
                    court: $court,
                    citation: $citation,
                    filename: $filename
                })
            """, **case_data)

    def add_citation(self, from_case_id, to_case_id, citation_text):
        """Add citation relationship between cases"""
        with self.driver.session() as session:
            session.run("""
                MATCH (from:Case {case_id: $from_case_id})
                MATCH (to:Case {case_id: $to_case_id})
                CREATE (from)-[:CITES {context: $citation_text}]->(to)
            """, from_case_id=from_case_id, to_case_id=to_case_id,
                citation_text=citation_text)

    def add_section(self, case_id, section_data, vector_id):
        """Link section to case and store Pinecone vector ID"""
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Case {case_id: $case_id})
                CREATE (s:Section {
                    section_id: $section_id,
                    section_type: $section_type,
                    content: $content,
                    confidence: $confidence,
                    vector_id: $vector_id
                })
                CREATE (c)-[:HAS_SECTION]->(s)
            """, case_id=case_id, vector_id=vector_id, **section_data)

    def find_related_cases(self, case_id, max_depth=2):
        """Find cases related through citations"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH path = (c:Case {case_id: $case_id})-[:CITES*1..$max_depth]-(related:Case)
                RETURN DISTINCT related.case_id, related.title, length(path) as distance
                ORDER BY distance
            """, case_id=case_id, max_depth=max_depth)
            return [dict(record) for record in result]

    def get_precedent_chain(self, case_id):
        """Get the precedent chain for a case"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH path = (c:Case {case_id: $case_id})-[:CITES*]->(precedent:Case)
                RETURN path
                ORDER BY length(path)
            """, case_id=case_id)
            return [dict(record) for record in result]
```

### Phase 4: Extract Legal Entities (Week 2-3)

Use NLP to extract entities from judgments:

```python
# Install: pip install spacy
# Download: python -m spacy download en_core_web_lg

import spacy

nlp = spacy.load("en_core_web_lg")

def extract_entities(text):
    """Extract legal entities from text"""
    doc = nlp(text)

    entities = {
        'persons': [],      # Judges, lawyers, parties
        'organizations': [], # Courts, legal firms
        'citations': [],    # Case citations (regex)
        'statutes': []      # Legal statutes (regex)
    }

    # Extract named entities
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            entities['persons'].append(ent.text)
        elif ent.label_ == "ORG":
            entities['organizations'].append(ent.text)

    # Extract case citations (regex pattern)
    import re
    citation_pattern = r'\d{4}\s+[A-Z]+\s+\d+'
    entities['citations'] = re.findall(citation_pattern, text)

    # Extract statute references
    statute_pattern = r'Section\s+\d+[A-Z]*'
    entities['statutes'] = re.findall(statute_pattern, text)

    return entities
```

### Phase 5: Hybrid Query Engine (Week 3-4)

Create `hybrid_search.py`:

```python
class HybridSearch:
    def __init__(self, vector_db, knowledge_graph):
        self.vector_db = vector_db
        self.kg = knowledge_graph

    def hybrid_search(self, query, top_k=10):
        """
        Combine vector similarity and graph relationships
        """
        # Step 1: Vector search (Pinecone)
        vector_results = self.vector_db.similarity_search(query, top_k=top_k*2)

        # Step 2: For each result, get graph context
        enriched_results = []
        for result in vector_results:
            case_id = result['metadata'].get('case_id')

            # Get related cases from knowledge graph
            related_cases = self.kg.find_related_cases(case_id, max_depth=2)

            # Calculate graph score (based on citation count, court hierarchy, etc.)
            graph_score = self._calculate_graph_score(case_id, related_cases)

            # Combine scores
            vector_score = result['similarity_score']
            hybrid_score = 0.6 * vector_score + 0.4 * graph_score

            enriched_results.append({
                **result,
                'graph_score': graph_score,
                'hybrid_score': hybrid_score,
                'related_cases': related_cases[:3]  # Top 3 related
            })

        # Re-rank by hybrid score
        enriched_results.sort(key=lambda x: x['hybrid_score'], reverse=True)

        return enriched_results[:top_k]

    def _calculate_graph_score(self, case_id, related_cases):
        """Calculate relevance based on graph structure"""
        # Example scoring logic:
        # - More citations = higher score
        # - Higher court = higher score
        # - Recent cases = higher score
        score = 0.5  # Base score

        # Boost for number of related cases
        score += min(len(related_cases) * 0.1, 0.3)

        return score
```

---

## Benefits You'll Get

### 1. Enhanced Retrieval Quality
- Find cases that are semantically similar (Pinecone)
- Find cases that are legally related (Neo4j)
- Best of both worlds!

### 2. Explainable Results
- "This case cites 5 precedents"
- "This judgment was delivered by the same judge"
- "This case applies the same legal principle"

### 3. Advanced Queries
```cypher
// Find all cases that cite a specific landmark judgment
MATCH (c:Case)-[:CITES]->(landmark:Case {citation: "1973 SCR 1461"})
RETURN c

// Find cases with similar reasoning patterns
MATCH (c1:Case)-[:HAS_SECTION]->(s1:Section {section_type: 'ratio_decidendi'}),
      (c2:Case)-[:HAS_SECTION]->(s2:Section {section_type: 'ratio_decidendi'})
WHERE s1.vector_id IN [vector_ids from Pinecone similarity search]
RETURN c1, c2

// Find judge-specific precedents
MATCH (judge:Judge)-[:DECIDED]->(case:Case)-[:CITES]->(precedent:Case)
WHERE judge.name = "Justice X"
RETURN precedent
```

### 4. Visualization
Neo4j Browser provides interactive graph visualization:
- See citation networks
- Explore legal reasoning chains
- Understand case relationships visually

---

## Performance Considerations

### Scalability
- **Pinecone**: Handles millions of vectors efficiently
- **Neo4j**: Can handle billions of nodes and relationships
- **Hybrid**: Query latency typically < 200ms

### Cost Estimates (Monthly)
- **Pinecone Serverless**: $0.10 per 1M queries (very affordable)
- **Neo4j AuraDB Free**: Up to 200k nodes (sufficient for 1000s of cases)
- **Neo4j AuraDB Pro**: Starting at $65/month for production

### Data Volume Estimates
- 10,000 legal cases
- ~90,000 sections (9 per case)
- ~50,000 citation relationships
- **Total**: ~150k nodes, 140k relationships (fits in free tier!)

---

## Migration Path

1. **Phase 1** (Week 1): Setup Neo4j, define schema
2. **Phase 2** (Week 2): Build graph loader, integrate with existing ingestion
3. **Phase 3** (Week 3): Add entity extraction
4. **Phase 4** (Week 4): Implement hybrid search
5. **Phase 5** (Week 5): Add advanced queries and visualization

**Estimated Total Time**: 4-5 weeks for full integration

---

## Next Steps

1. **Decision**: Choose Neo4j AuraDB (cloud) or self-hosted
2. **Prototype**: Start with 10-20 sample cases
3. **Extract**: Add citation extraction to your PDF ingestion pipeline
4. **Build**: Implement the hybrid search engine
5. **Evaluate**: Compare results with vector-only approach
6. **Scale**: Gradually migrate your full corpus

---

## Sample Implementation: Adding to Your Current Pipeline

Modify `create_database.py` to also populate the knowledge graph:

```python
from vectordb import VectorDatabase
from graphdb import KnowledgeGraph  # New
import uuid

def process_document(pdf_path, vector_db, knowledge_graph):
    # Existing: Extract sections, create embeddings
    sections = extract_sections(pdf_path)

    # New: Create case node
    case_id = str(uuid.uuid4())
    knowledge_graph.add_case({
        'case_id': case_id,
        'title': extract_title(pdf_path),
        'year': extract_year(pdf_path),
        'filename': pdf_path.name
    })

    # Process each section
    for section in sections:
        # Existing: Add to Pinecone
        vector_id = vector_db.add_document(section)

        # New: Link section to case in Neo4j
        knowledge_graph.add_section(
            case_id=case_id,
            section_data={
                'section_id': str(uuid.uuid4()),
                'section_type': section.type,
                'content': section.content[:500],  # First 500 chars
                'confidence': section.confidence
            },
            vector_id=vector_id
        )

        # New: Extract and add citations
        citations = extract_citations(section.content)
        for citation in citations:
            # Find or create cited case
            cited_case_id = find_or_create_case(citation)
            knowledge_graph.add_citation(case_id, cited_case_id, citation)
```

---

## Questions?

This guide provides a comprehensive roadmap. The knowledge graph will transform your retrieval system from "find similar text" to "understand legal relationships."

**Ready to implement?** Start with Phase 1 and prototype with a small dataset!
