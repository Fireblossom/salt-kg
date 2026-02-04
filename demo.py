"""
Demo: Agentic Scripting Solver for SALT-KG

This script demonstrates the "Code as Reasoning" approach where an LLM
generates Python prediction functions based on business knowledge from
the Knowledge Graph, instead of using traditional ML.

Usage:
    python demo.py                    # Run with mock LLM (no API key needed)
    python demo.py --provider openai  # Use OpenAI (requires OPENAI_API_KEY)
    python demo.py --provider anthropic  # Use Anthropic (requires ANTHROPIC_API_KEY)
"""

import argparse
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from agentic_solver import AgenticPredictor, KGLoader
from agentic_solver.script_generator import ScriptGenerator
from agentic_solver.script_improver import ScriptImprover


def load_data():
    """Load SALT-KG training and test data"""
    data_path = Path(__file__).parent / 'data' / 'salt'

    print("Loading data...")
    train_df = pd.read_parquet(data_path / 'JoinedTables_train.parquet')
    test_df = pd.read_parquet(data_path / 'JoinedTables_test.parquet')
    print(f"   Loaded parquet files")

    print(f"   Train: {len(train_df)} rows, {len(train_df.columns)} columns")
    print(f"   Test:  {len(test_df)} rows")

    return train_df, test_df


def explore_kg():
    """Explore the Knowledge Graph structure"""
    print("\n" + "="*60)
    print("KNOWLEDGE GRAPH EXPLORATION")
    print("="*60)

    kg = KGLoader()

    print("\nAvailable Views:")
    for view_name, view in kg.views.items():
        print(f"\n  {view_name}:")
        print(f"    Description: {view.description}")
        print(f"    Fields: {len(view.fields)}")

        # Show target fields
        targets = view.get_target_fields()
        if targets:
            print(f"    Target Fields: {[t.field_name for t in targets]}")

    # Show example field metadata
    print("\nExample Field Metadata (SALESGROUP):")
    field = kg.get_field('SALESGROUP')
    if field:
        print(f"    Name: {field.field_name}")
        print(f"    Description: {field.field_description}")
        print(f"    Type: {field.field_type}")
        print(f"\n    Business Rules:")
        for line in field.get_business_rules().split('\n')[:10]:
            print(f"      {line}")


def demo_prediction(train_df: pd.DataFrame, test_df: pd.DataFrame,
                    target_field: str, provider: str):
    """Demonstrate prediction on a target field"""
    print("\n" + "="*60)
    print(f"PREDICTING: {target_field}")
    print("="*60)

    # Initialize predictor
    predictor = AgenticPredictor(
        llm_provider=provider,
        verbose=True
    )

    # Fit (generate prediction script)
    print("\nStep 1: Generating prediction script...")
    predictor.fit(target_field, train_df)

    # Show generated code
    print("\nGenerated Code:")
    print("-" * 40)
    code = predictor.get_generated_code()
    for line in code.split('\n'):
        print(f"  {line}")
    print("-" * 40)

    # Show explanation
    print(f"\nLLM Explanation: {predictor.get_explanation()}")

    # Make predictions
    print("\nStep 2: Making predictions...")
    predictions = predictor.predict(test_df.head(100))

    # Show sample predictions
    print("\nSample Predictions (first 10):")
    if target_field in test_df.columns:
        comparison = pd.DataFrame({
            'Actual': test_df[target_field].head(10).values,
            'Predicted': predictions.head(10).values
        })
        comparison['Match'] = comparison['Actual'] == comparison['Predicted']
        print(comparison.to_string())
    else:
        print(predictions.head(10))

    # Evaluate
    if target_field in test_df.columns:
        print("\nStep 3: Evaluating...")
        report = predictor.evaluate(test_df.head(100))
        print(f"   Accuracy: {report.accuracy:.1%}" if report.accuracy else "   Accuracy: N/A")
        print(f"   Coverage: {report.predicted_count}/{report.total_rows} ({report.predicted_count/report.total_rows:.1%})")
        print(f"   Unique predictions: {report.unique_predictions}")

    return predictor


def compare_approaches(train_df: pd.DataFrame, test_df: pd.DataFrame,
                       target_field: str):
    """Compare agentic approach with simple baseline"""
    print("\n" + "="*60)
    print("COMPARISON: Agentic vs Baseline")
    print("="*60)

    if target_field not in test_df.columns:
        print("   Target field not in test data, skipping comparison")
        return

    # Baseline: Most frequent value
    most_common = train_df[target_field].mode()[0]
    baseline_preds = pd.Series([most_common] * len(test_df), index=test_df.index)

    baseline_acc = (baseline_preds == test_df[target_field]).mean()
    print(f"\nBaseline (Most Frequent = '{most_common}'):")
    print(f"   Accuracy: {baseline_acc:.1%}")

    # Agentic prediction
    predictor = AgenticPredictor(llm_provider="mock", verbose=False)
    predictor.fit(target_field, train_df)
    agentic_preds = predictor.predict(test_df)

    agentic_acc = (agentic_preds == test_df[target_field]).mean()
    print(f"\n🤖 Agentic (Code as Reasoning):")
    print(f"   Accuracy: {agentic_acc:.1%}")

    # Comparison
    diff = agentic_acc - baseline_acc
    if diff > 0:
        print(f"\nAgentic is better by {diff:.1%}")
    elif diff < 0:
        print(f"\nBaseline is better by {-diff:.1%}")
    else:
        print(f"\nBoth approaches have same accuracy")

    # Show where agentic wins
    agentic_correct = agentic_preds == test_df[target_field]
    baseline_correct = baseline_preds == test_df[target_field]
    agentic_wins = (agentic_correct & ~baseline_correct).sum()
    baseline_wins = (~agentic_correct & baseline_correct).sum()

    print(f"\n   Cases where Agentic wins: {agentic_wins}")
    print(f"   Cases where Baseline wins: {baseline_wins}")


def demo_improve(train_df: pd.DataFrame, test_df: pd.DataFrame,
                  target_field: str, provider: str):
    """Demonstrate script improvement with DuckDB SQL analysis"""
    print("\n" + "="*60)
    print(f"IMPROVING SCRIPT: {target_field}")
    print("   Using DuckDB SQL analysis for pattern discovery")
    print("="*60)
    
    # Check if saved script exists
    script_path = Path(__file__).parent / 'agentic_solver' / 'saved_scripts' / f'{target_field.lower()}.py'
    if not script_path.exists():
        print(f"\nNo saved script found for {target_field}")
        print(f"   Expected: {script_path}")
        print("   Run with --target to generate one first, or use a field with existing script")
        return None
    
    # Initialize
    print("\nInitializing with DuckDB analyzer...")
    gen = ScriptGenerator(provider=provider)
    imp = ScriptImprover(gen, verbose=True)
    
    # Run improvement loop
    print("\nRunning improvement loop (SQL analysis + error analysis)...")
    try:
        initial_acc, final_acc = imp.improve_and_save(
            target_field,
            train_df,
            test_df,
            max_iterations=2,
            use_sql_analysis=True
        )
        
        print("\n" + "-"*40)
        print(f"Results:")
        print(f"   Initial Accuracy: {initial_acc:.2%}")
        print(f"   Final Accuracy:   {final_acc:.2%}")
        if final_acc > initial_acc:
            print(f"   Improvement: +{(final_acc - initial_acc):.2%}")
        else:
            print(f"   No improvement found")
        print("-"*40)
        
    except Exception as e:
        print(f"\nError during improvement: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    return imp


def main():
    parser = argparse.ArgumentParser(description='Agentic Scripting Solver Demo')
    parser.add_argument('--provider', choices=['mock', 'openai', 'anthropic'],
                        default='mock', help='LLM provider to use')
    parser.add_argument('--target', type=str, default='SALESGROUP',
                        help='Target field to predict')
    parser.add_argument('--skip-exploration', action='store_true',
                        help='Skip KG exploration')
    parser.add_argument('--improve', action='store_true',
                        help='Run ScriptImprover with DuckDB SQL analysis')
    args = parser.parse_args()

    print("="*60)
    print("AGENTIC SCRIPTING SOLVER FOR SALT-KG")
    print("   'Code as Reasoning' - LLM generates logic, CPU executes")
    print("="*60)

    # Load data
    try:
        train_df, test_df = load_data()
    except Exception as e:
        print(f"\nError loading data: {e}")
        print("   Make sure you're running from the salt-kg directory")
        return 1

    # Explore KG
    if not args.skip_exploration:
        explore_kg()

    # Demo prediction
    try:
        predictor = demo_prediction(train_df, test_df, args.target, args.provider)
    except Exception as e:
        print(f"\nError during prediction: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Compare approaches
    compare_approaches(train_df, test_df, args.target)
    
    # Optionally run improvement demo
    if args.improve:
        demo_improve(train_df, test_df, args.target, args.provider)

    print("\n" + "="*60)
    print("Demo completed!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
