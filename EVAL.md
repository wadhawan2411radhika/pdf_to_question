# Evaluation System Design

## Functional Requirements

### Core Extraction Requirements:
1. **Question Detection & Extraction**: System must identify and extract questions from PDFs with varying formats (numbered, titled, embedded in tables)
2. **Multi-Part Question Handling**: Support nested question structures (Q1(a)(i)) with proper hierarchy preservation
3. **MCQ Option Extraction**: Capture multiple-choice options with letter-based formatting (A:, B:, C:, etc.)
4. **Asset Linking**: Associate images and tables with relevant questions/subparts based on spatial relationships
5. **LaTeX Processing**: Detect and render mathematical expressions and symbols
6. **Structured Output**: Generate valid JSON conforming to defined schema with proper asset references
7. **Cross-Format Support**: Handle both text-dominant and table-dominant PDF layouts

### API Requirements:
1. **Input Interface**: Accept PDF file path via POST /extract endpoint
2. **Output Interface**: Return JSON file path and assets directory location
3. **Error Handling**: Provide meaningful error responses for processing failures
4. **Batch Processing**: Support evaluation script execution for multiple PDFs

## Non-Functional Requirements

### Performance Requirements:
1. **Runtime Constraint**: ≤3 minutes per PDF (up to 10 pages)
2. **Parallelism**: Support ≥5 PDFs processing concurrently without crashes
3. **Memory Efficiency**: Handle multiple large PDFs without memory overflow
4. **Graceful Degradation**: Continue processing with partial failures, log errors appropriately

### Quality Requirements:
1. **Accuracy**: High precision in question-asset associations (target >80%)
2. **Completeness**: High recall for question detection (target >90%)
3. **Consistency**: Deterministic results across multiple runs
4. **Robustness**: Handle edge cases (malformed PDFs, unusual layouts, missing elements)

### System Requirements:
1. **Schema Compliance**: 100% conformance to defined JSON schema
2. **Asset Management**: Proper file organization and referencing
3. **Logging**: Comprehensive error and processing logs
4. **Modularity**: Clean, maintainable code architecture

## Evaluation Methodology

### 1. Ground Truth Creation
**Manual Annotation Process**: For each of the 5 dev set PDFs, create comprehensive ground truth annotations including:
- Complete question text with exact numbering
- All subpart structures (Q1(a)(i) hierarchies)
- MCQ options with proper formatting
- Image-to-question associations with spatial coordinates
- Table-to-question mappings
- LaTeX expressions with expected rendering

**Ground Truth Format**: Schema-compliant JSON structure matching our output format for direct comparison.

### 2. Functional Requirements Evaluation

#### Question Detection Accuracy
**Metrics**: Precision, Recall, F1-score for question identification
- **Document-level**: Overall question detection rate per PDF
- **Page-level**: Question detection consistency across pages
- **Edge Cases**: Cross-page questions, irregular numbering, embedded questions

#### Multi-Part Structure Preservation
**Metrics**: Tree Edit Distance for hierarchical structure comparison
- **Structure Accuracy**: Correct nesting of subparts
- **Completeness**: Percentage of ground truth subparts captured
- **Ordering**: Sequence preservation for question components

#### MCQ Option Extraction
**Metrics**: BLEU/ROUGE scores for text accuracy, option detection rate
- **Format Handling**: Standard A-E options vs. non-standard formats
- **Layout Robustness**: Performance across different option layouts
- **Completeness**: All options captured per question

#### Asset Association Accuracy
**Metrics**: Precision/Recall for image and table linking
- **Spatial Accuracy**: Bounding box overlap for correctly associated assets
- **Question-level**: Assets linked to correct main questions
- **Subpart-level**: Granular association evaluation

#### LaTeX Processing Evaluation
**Metrics**: Symbol detection recall, expression completeness
- **Basic Symbols**: Common mathematical notation (±, ×, ÷, etc.)
- **Complex Expressions**: Fractions, integrals, summations
- **Rendering Fidelity**: Visual similarity assessment

### 3. Non-Functional Requirements Evaluation

#### Performance Testing
**Runtime Compliance**: Automated timing for each PDF with 3-minute threshold
- **Metrics**: Compliance rate, average processing time, outlier analysis
- **Scalability**: Performance degradation with PDF complexity

**Parallelism Testing**: Concurrent processing of 5+ PDFs
- **Metrics**: Success rate under load, memory usage patterns, crash frequency
- **Stability**: Error recovery and graceful degradation

#### Quality Assessment
**Accuracy Benchmarking**: Compare against manually verified ground truth
- **Semantic Similarity**: Sentence embedding cosine similarity (>0.8 threshold)
- **Content Coverage**: ROUGE scores for comprehensive extraction

**Consistency Testing**: Multiple runs with identical inputs
- **Deterministic Behavior**: Identical outputs across runs
- **Error Reproducibility**: Consistent failure patterns

## Rubric-Based Evaluation Framework

### 1. Key Constraints Compliance (30% Weight)
**Runtime Performance**: Percentage of PDFs processed within 3-minute limit
**Parallelism**: Binary pass/fail for concurrent processing of 5+ PDFs
**Stability & Logging**: Quality of error handling and log informativeness

**Scoring Method**: Weighted average of compliance rates with penalty for constraint violations

### 2. Correctness on Dev Set (25% Weight)
**Structural Fidelity**: Accuracy across MCQ options, multi-part hierarchy, table structure, figure linking
**Content Accuracy**: BLEU/ROUGE scores for extracted text vs. ground truth
**Asset Association**: Precision/recall for image and table mappings

**Scoring Method**: Macro-averaged F1 scores across all functional requirements

### 3. Structural Correctness (Schema) (20% Weight)
**JSON Schema Compliance**: Validation against defined schema using jsonschema library
**Asset Reference Integrity**: Verification that referenced files exist and are accessible
**Data Type Consistency**: Proper formatting of numbers, strings, arrays

**Scoring Method**: Binary compliance rate with deductions for schema violations

### 4. Code Quality & Runability (15% Weight)
**Batch Script Functionality**: run_eval.sh executes successfully with proper output
**Error Handling**: Graceful failure modes with informative error messages
**Modularity**: Clean separation of concerns and maintainable architecture
**Deterministic Execution**: Consistent results across multiple runs

**Scoring Method**: Manual assessment with standardized checklist

### 5. Approach & Communication (10% Weight)
**Documentation Quality**: Clarity of assumptions, trade-offs, and limitations in NOTES.md
**Baseline vs. Improvement**: Clear articulation of enhancements made
**Next Steps**: Prioritized and actionable improvement roadmap
**Technical Communication**: Appropriate level of detail for target audience

**Scoring Method**: Qualitative assessment using structured evaluation criteria

## Implementation Strategy

### Phase 1: Ground Truth Preparation
- Manual annotation of 5 dev set PDFs by domain expert
- Cross-validation of annotations for consistency
- Schema-compliant JSON generation for automated comparison

### Phase 2: Automated Testing Pipeline
- Runtime compliance testing with timing measurements
- Parallelism stress testing with resource monitoring
- Schema validation using standard JSON validation libraries
- Functional accuracy assessment with statistical metrics

### Phase 3: Qualitative Assessment
- Code review for modularity and maintainability
- Documentation evaluation for clarity and completeness
- Manual verification of edge cases and error handling

### Phase 4: Scoring and Reporting
- Weighted score calculation based on rubric percentages
- Detailed breakdown by requirement category
- Identification of strengths and improvement areas
- Actionable recommendations for system enhancement
