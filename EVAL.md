Evaluation System Design
Functional Requirements
Core Extraction Requirements:
1. Question Detection & Extraction: System must identify and extract questions from PDFs with varying formats (numbered, titled, embedded in tables)
2. Multi-Part Question Handling: Support nested question structures (Q1(a)(i)) with proper hierarchy preservation
3. MCQ Option Extraction: Capture multiple-choice options with letter-based formatting (A:, B:, C:, etc.)
4. Asset Linking: Associate images and tables with relevant questions/subparts based on spatial relationships
5. LaTeX Processing: Detect and render mathematical expressions and symbols
6. Structured Output: Generate valid JSON conforming to defined schema with proper asset references
7. Cross-Format Support: Handle both text-dominant and table-dominant PDF layouts
API Requirements:
1. Input Interface: Accept PDF file path via POST /extract endpoint
2. Output Interface: Return JSON file path and assets directory location
3. Error Handling: Provide meaningful error responses for processing failures
4. Batch Processing: Support evaluation script execution for multiple PDFs
Non-Functional Requirements
Performance Requirements:
1. Runtime Constraint: ≤3 minutes per PDF (up to 10 pages)
2. Parallelism: Support ≥5 PDFs processing concurrently without crashes
3. Memory Efficiency: Handle multiple large PDFs without memory overflow
4. Graceful Degradation: Continue processing with partial failures, log errors appropriately
Quality Requirements:
1. Accuracy: High precision in question-asset associations (target >80%)
2. Completeness: High recall for question detection (target >90%)
3. Consistency: Deterministic results across multiple runs
4. Robustness: Handle edge cases (malformed PDFs, unusual layouts, missing elements)
System Requirements:
1. Schema Compliance: 100% conformance to defined JSON schema
2. Asset Management: Proper file organization and referencing
3. Logging: Comprehensive error and processing logs
4. Modularity: Clean, maintainable code architecture
Functional Requirements Evaluation Methodology
1. Question Detection Accuracy
Method: Compare extracted questions against manually annotated ground truth
* Metrics: Precision, Recall, F1-score for question identification
* Levels: Document-level, page-level question detection rates
* Edge Cases: Handle irregular numbering, embedded questions, cross-page questions
2. Multi-Part Structure Preservation
Method: Validate hierarchical question structure extraction
* Metrics: Structure accuracy (correct nesting), completeness (all subparts captured)
* Test Cases: Complex nested structures (Q1(a)(i)(α)), mixed formats
* Validation: Tree structure comparison between ground truth and extracted hierarchy
3. MCQ Option Extraction
Method: Verify option detection and text extraction accuracy
* Metrics: Option detection rate, text accuracy (BLEU/ROUGE scores)
* Edge Cases: Non-standard option formats, varying layouts, embedded images
* Validation: Character-level and semantic-level option comparison
4. Asset Association Accuracy
Method: Evaluate image and table linking precision
* Metrics: Correct association rate, false positive rate, spatial accuracy
* Levels: Question-level and subpart-level association evaluation
* Ground Truth: Manual annotation of correct question-asset pairs
5. LaTeX Processing Evaluation
Method: Compare LaTeX detection and rendering accuracy
* Metrics: Symbol detection recall, rendering accuracy, format preservation
* Test Cases: Mathematical expressions, special symbols, complex equations
* Validation: Visual and textual comparison of rendered output
Non-Functional Requirements Evaluation Methodology
Performance Evaluation Framework
1. Runtime Compliance Testing
# Automated timing evaluation
for pdf in test_set/*.pdf; do
    start_time=$(date +%s.%N)
    python extract.py "$pdf"
    end_time=$(date +%s.%N)
    runtime=$(echo "$end_time - $start_time" | bc)
    echo "$pdf: ${runtime}s"
done
Metrics:
* Percentage of PDFs meeting ≤3min constraint
* Average processing time per page
* Time distribution analysis and outlier identification
2. Parallelism & Stability Testing
# Concurrent processing test
parallel -j 5 python extract.py ::: test_set/*.pdf
Metrics:
* Success rate under concurrent load
* Memory usage patterns during parallel execution
* Error rate and crash frequency analysis
* Log completeness and error reporting quality
Accuracy Evaluation Framework
1. Ground Truth Creation Protocol
Process:
1. Manual annotation of 5 dev set PDFs with complete question structures
2. Asset association mapping (images/tables to questions/subparts)
3. LaTeX expression identification and expected rendering
4. Schema-compliant JSON format for ground truth data
Ground Truth Structure:
{
  "pdf_name": "test1.pdf",
  "questions": [
    {
      "question_number": "1",
      "question_text": "Calculate the derivative...",
      "latex_elements": ["\\frac{d}{dx}", "x^2"],
      "subparts": [...],
      "mcq_options": [...],
      "associated_assets": ["image_001.png", "table_002.csv"]
    }
  ]
}
2. Semantic Matching & Scoring
Question Text Evaluation:
* BLEU Score: N-gram precision for extracted vs ground truth text
* ROUGE Score: Recall-oriented evaluation for content coverage
* Semantic Similarity: Sentence embedding cosine similarity (>0.8 threshold)
Hierarchical Structure Evaluation:
* Tree Edit Distance: Measure structural similarity for multi-part questions
* Completeness Score: Percentage of ground truth subparts correctly identified
* Ordering Accuracy: Correct sequence preservation for question parts
3. Asset Association Evaluation
Image Mapping Accuracy:
def evaluate_image_mapping(ground_truth, extracted):
    correct_mappings = 0
    total_mappings = len(ground_truth['image_associations'])
    
    for gt_mapping in ground_truth['image_associations']:
        if find_matching_association(gt_mapping, extracted):
            correct_mappings += 1
    
    return correct_mappings / total_mappings
Metrics:
* Precision: Correct associations / Total extracted associations
* Recall: Correct associations / Total ground truth associations
* Spatial Accuracy: Bounding box overlap for correctly associated assets
4. LaTeX Processing Evaluation
Detection Accuracy:
* Symbol Recall: Percentage of LaTeX symbols correctly identified
* Expression Completeness: Full mathematical expression capture rate
* Rendering Fidelity: Visual similarity of rendered output
Metrics Calculation:
def evaluate_latex_processing(ground_truth_latex, extracted_latex):
    detected_symbols = set(extract_latex_symbols(extracted_latex))
    true_symbols = set(extract_latex_symbols(ground_truth_latex))
    
    precision = len(detected_symbols & true_symbols) / len(detected_symbols)
    recall = len(detected_symbols & true_symbols) / len(true_symbols)
    
    return precision, recall, 2 * precision * recall / (precision + recall)
Rubric-Based Evaluation Framework
1. Key Constraints Compliance (30% Weight)
Runtime Performance Evaluation:
# Automated runtime testing
#!/bin/bash
total_pdfs=0
exceeded_pdfs=0
total_overshoot=0

for pdf in data/dev/*.pdf; do
    start_time=$(date +%s.%N)
    python src/main.py --pdf_path "$pdf" --output_dir "outputs/"
    end_time=$(date +%s.%N)
    runtime=$(echo "$end_time - $start_time" | bc)
    
    total_pdfs=$((total_pdfs + 1))
    if (( $(echo "$runtime > 180" | bc -l) )); then
        exceeded_pdfs=$((exceeded_pdfs + 1))
        overshoot=$(echo "$runtime - 180" | bc)
        total_overshoot=$(echo "$total_overshoot + $overshoot" | bc)
    fi
    
    echo "PDF: $pdf, Runtime: ${runtime}s"
done

compliance_rate=$(echo "scale=2; (($total_pdfs - $exceeded_pdfs) / $total_pdfs) * 100" | bc)
avg_overshoot=$(echo "scale=2; $total_overshoot / $exceeded_pdfs" | bc)
echo "Runtime Compliance: ${compliance_rate}%"
echo "Average Overshoot: ${avg_overshoot}s"
Parallelism Testing:
# Test concurrent processing stability
parallel --jobs 5 --halt soon,fail=1 python src/main.py --pdf_path {} --output_dir outputs/ ::: data/dev/*.pdf
exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "Parallelism Test: PASSED"
else
    echo "Parallelism Test: FAILED"
fi
Stability & Error Logging Assessment:
* Log File Presence: Check for comprehensive logging in designated log directory
* Error Response Quality: Validate API returns meaningful error messages with status codes
* Graceful Degradation: System continues processing despite individual PDF failures
2. Correctness on Dev Set (25% Weight)
Structural Fidelity Evaluation:
def evaluate_structural_correctness(ground_truth_dir, extracted_dir):
    scores = {
        'mcq_options': [],
        'multipart_hierarchy': [],
        'table_structure': [],
        'figure_linking': []
    }
    
    for pdf_name in os.listdir(ground_truth_dir):
        gt_data = load_ground_truth(f"{ground_truth_dir}/{pdf_name}")
        extracted_data = load_extracted(f"{extracted_dir}/{pdf_name}")
        
        # MCQ Options Evaluation
        mcq_score = evaluate_mcq_extraction(gt_data, extracted_data)
        scores['mcq_options'].append(mcq_score)
        
        # Multi-part Hierarchy Evaluation
        hierarchy_score = evaluate_hierarchy_preservation(gt_data, extracted_data)
        scores['multipart_hierarchy'].append(hierarchy_score)
        
        # Table Structure Evaluation
        table_score = evaluate_table_structure(gt_data, extracted_data)
        scores['table_structure'].append(table_score)
        
        # Figure Linking Evaluation
        figure_score = evaluate_figure_associations(gt_data, extracted_data)
        scores['figure_linking'].append(figure_score)
    
    return {metric: np.mean(values) for metric, values in scores.items()}
3. Structural Correctness (Schema) (20% Weight)
Schema Validation Testing:
import jsonschema
from jsonschema import validate

def validate_schema_compliance(output_dir, schema_file):
    with open(schema_file, 'r') as f:
        schema = json.load(f)
    
    compliance_results = []
    image_reference_results = []
    
    for output_file in glob.glob(f"{output_dir}/*.json"):
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        # Schema Validation
        try:
            validate(instance=data, schema=schema)
            compliance_results.append(1)
        except jsonschema.exceptions.ValidationError:
            compliance_results.append(0)
        
        # Image Reference Validation
        image_ref_score = validate_image_references(data, output_dir)
        image_reference_results.append(image_ref_score)
    
    schema_compliance = np.mean(compliance_results) * 100
    image_ref_accuracy = np.mean(image_reference_results) * 100
    
    return {
        'schema_compliance_rate': schema_compliance,
        'image_reference_accuracy': image_ref_accuracy
    }
4. Code Quality & Runability (15% Weight)
Automated Code Quality Assessment:
# LLM-based code quality evaluation
def evaluate_code_quality_with_llm(codebase_path):
    criteria = {
        'modularity': "Assess code organization, separation of concerns, and module structure",
        'clarity': "Evaluate code readability, naming conventions, and documentation",
        'deterministic_behavior': "Check for consistent outputs across multiple runs",
        'error_handling': "Assess robustness of error handling and edge case management"
    }
    
    scores = {}
    for criterion, prompt in criteria.items():
        # Use LLM to evaluate code quality based on criterion
        score = llm_evaluate_code(codebase_path, prompt)
        scores[criterion] = score
    
    return scores

# Batch Script Functionality Test
def test_batch_script():
    result = subprocess.run(['bash', 'run_eval.sh', 'data/dev/*.pdf', 'outputs/'], 
                          capture_output=True, text=True)
    return {
        'script_executes': result.returncode == 0,
        'processing_times_reported': 'processing time' in result.stdout.lower(),
        'validation_errors_reported': 'error' in result.stdout.lower() or 'validation' in result.stdout.lower()
    }
5. Approach & Communication (10% Weight)
Documentation Quality Assessment:
def evaluate_documentation_quality(notes_file):
    with open(notes_file, 'r') as f:
        content = f.read()
    
    # LLM-based evaluation criteria
    evaluation_prompts = {
        'assumptions_clarity': "Rate the clarity and completeness of stated assumptions (1-10)",
        'tradeoffs_explanation': "Evaluate the quality of trade-off explanations and rationale (1-10)",
        'baseline_improvement': "Assess the clarity of baseline vs improvement description (1-10)",
        'limitations_honesty': "Rate the honesty and completeness of limitation discussions (1-10)",
        'next_steps_prioritization': "Evaluate the quality and prioritization of next steps (1-10)"
    }
    
    scores = {}
    for criterion, prompt in evaluation_prompts.items():
        # Use LLM to evaluate documentation quality
        score = llm_evaluate_documentation(content, prompt)
        scores[criterion] = score
    
    return scores
Comprehensive Evaluation Pipeline
Automated Evaluation Script:
#!/usr/bin/env python3
"""
Comprehensive evaluation pipeline for PDF question extraction system
"""

def run_complete_evaluation():
    results = {}
    
    # 1. Key Constraints Compliance (30%)
    print("Evaluating Key Constraints Compliance...")
    runtime_results = evaluate_runtime_compliance()
    parallelism_results = evaluate_parallelism()
    stability_results = evaluate_stability_logging()
    
    constraints_score = (
        runtime_results['compliance_rate'] * 0.4 +
        parallelism_results['success_rate'] * 0.3 +
        stability_results['logging_quality'] * 0.3
    )
    results['constraints_compliance'] = constraints_score
    
    # 2. Correctness on Dev Set (25%)
    print("Evaluating Correctness on Dev Set...")
    correctness_results = evaluate_structural_correctness('ground_truth/', 'outputs/')
    correctness_score = np.mean(list(correctness_results.values()))
    results['dev_set_correctness'] = correctness_score
    
    # 3. Structural Correctness (20%)
    print("Evaluating Structural Correctness...")
    schema_results = validate_schema_compliance('outputs/', 'schema.json')
    structural_score = (
        schema_results['schema_compliance_rate'] * 0.7 +
        schema_results['image_reference_accuracy'] * 0.3
    )
    results['structural_correctness'] = structural_score
    
    # 4. Code Quality & Runability (15%)
    print("Evaluating Code Quality...")
    code_quality_results = evaluate_code_quality_with_llm('src/')
    batch_results = test_batch_script()
    quality_score = (
        np.mean(list(code_quality_results.values())) * 0.7 +
        np.mean(list(batch_results.values())) * 0.3
    )
    results['code_quality'] = quality_score
    
    # 5. Approach & Communication (10%)
    print("Evaluating Documentation Quality...")
    doc_results = evaluate_documentation_quality('NOTES.md')
    communication_score = np.mean(list(doc_results.values()))
    results['communication'] = communication_score
    
    # Calculate weighted final score
    final_score = (
        results['constraints_compliance'] * 0.30 +
        results['dev_set_correctness'] * 0.25 +
        results['structural_correctness'] * 0.20 +
        results['code_quality'] * 0.15 +
        results['communication'] * 0.10
    )
    
    results['final_weighted_score'] = final_score
    
    # Generate comprehensive report
    generate_evaluation_report(results)
    
    return results

if __name__ == "__main__":
    evaluation_results = run_complete_evaluation()
    print(f"Final Evaluation Score: {evaluation_results['final_weighted_score']:.2f}/100")
This comprehensive evaluation framework provides systematic assessment across all rubric categories with quantitative metrics, automated testing procedures, and detailed scoring mechanisms aligned with the problem statement requirements.
