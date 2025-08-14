#!/usr/bin/env python3
"""
Script to clean the 5 problematic layers identified in validation:
- amenities, pt_stops, test_buildings, test_cycle, test_landuse

Addresses:
- Invalid geometries (self-intersections, topology errors)  
- Duplicate features (geometry and osmid duplicates)
- Tiny features below minimum size thresholds
"""

import sys
import time
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, 'src')

from etl.data_cleaner import clean_staging_data
from etl.validation import validate_pipeline_data
from etl.utils import ensure_directory

def clean_problematic_layers():
    """Clean the 5 layers with known quality issues."""
    start_time = time.time()
    
    print("🧹 Cleaning Problematic Layers")
    print("=" * 50)
    
    # The 5 problematic layers identified in validation
    problematic_layers = [
        "amenities", 
        "pt_stops", 
        "test_buildings", 
        "test_cycle", 
        "test_landuse"
    ]
    
    staging_dir = Path("data/staging")
    validation_dir = Path("data/validation")
    
    print(f"🎯 Target layers: {', '.join(problematic_layers)}")
    print(f"📁 Staging directory: {staging_dir}")
    
    # Step 1: Clean the data
    print("\n🔧 STEP 1: Data Cleaning")
    print("-" * 30)
    
    try:
        cleaning_results = clean_staging_data(
            staging_dir=staging_dir,
            layers=problematic_layers,
            backup=True
        )
        
        if "error" in cleaning_results:
            print(f"❌ Cleaning failed: {cleaning_results['error']}")
            return False
        
        # Display cleaning summary
        print(f"\n✅ Cleaning completed:")
        for layer_name, layer_result in cleaning_results.get("layers", {}).items():
            if layer_result.get("success", False):
                original = layer_result["original_features"]
                final = layer_result["final_features"]
                removed = layer_result.get("features_removed_total", 0)
                repaired = layer_result.get("repaired_features", 0)
                
                print(f"  📊 {layer_name}: {original} → {final} features "
                      f"({removed} removed, {repaired} repaired)")
            else:
                print(f"  ❌ {layer_name}: Failed - {layer_result.get('error', 'Unknown error')}")
        
    except Exception as e:
        print(f"❌ Error during cleaning: {str(e)}")
        return False
    
    # Step 2: Re-validate cleaned data
    print("\n🔍 STEP 2: Post-Cleaning Validation")
    print("-" * 30)
    
    try:
        ensure_directory(validation_dir)
        
        # Only validate the problematic layers + test files
        validation_results = validate_pipeline_data(
            staging_dir=staging_dir,
            output_dir=validation_dir,
            include_tests=True
        )
        
        # Focus on our problematic layers
        cleaned_layer_results = {
            name: result for name, result in validation_results.items() 
            if any(prob_layer in name for prob_layer in problematic_layers)
        }
        
        # Summary of validation results
        total_layers = len(cleaned_layer_results)
        passed_layers = sum(1 for r in cleaned_layer_results.values() if r.is_valid)
        failed_layers = total_layers - passed_layers
        
        print(f"\n📊 Validation Results:")
        print(f"  • Total layers checked: {total_layers}")
        print(f"  • ✅ Passed: {passed_layers}")
        print(f"  • ❌ Failed: {failed_layers}")
        
        # Detailed results
        for layer_name, result in cleaned_layer_results.items():
            status = "✅ PASS" if result.is_valid else "❌ FAIL"
            print(f"  {status} {layer_name}: {result.success_rate:.1f}% success rate, {result.total_features} features")
            
            if not result.is_valid and result.errors:
                for error in result.errors[:2]:  # Show first 2 errors
                    print(f"    ⚠️ {error}")
        
        # Overall success
        improvement = passed_layers > 0
        print(f"\n🎯 IMPROVEMENT: {'✅ Yes' if improvement else '❌ No'}")
        
    except Exception as e:
        print(f"❌ Error during validation: {str(e)}")
        return False
    
    # Summary
    total_time = time.time() - start_time
    
    print("\n" + "=" * 50)
    print("🎯 CLEANING SUMMARY")
    print("=" * 50)
    
    if "summary" in cleaning_results:
        summary = cleaning_results["summary"]
        print(f"📊 Files processed: {summary['files_processed']}")
        print(f"🗑️ Features removed: {summary['features_removed']:,} ({summary['removal_rate']}%)")
    
    print(f"🔍 Validation: {passed_layers}/{total_layers} layers now passing")
    print(f"⏱️ Total time: {total_time:.1f}s")
    
    # Save results
    results_file = Path("data/validation/cleaning_results.json")
    ensure_directory(results_file.parent)
    
    final_results = {
        "timestamp": time.time(),
        "cleaning_results": cleaning_results,
        "validation_summary": {
            "total_layers": total_layers,
            "passed_layers": passed_layers,
            "failed_layers": failed_layers,
            "layer_details": {name: {"is_valid": result.is_valid, "success_rate": result.success_rate} 
                            for name, result in cleaned_layer_results.items()}
        },
        "total_time_seconds": round(total_time, 1)
    }
    
    with open(results_file, 'w') as f:
        json.dump(final_results, f, indent=2, default=str)
    
    print(f"📁 Results saved: {results_file}")
    print("=" * 50)
    
    return passed_layers > failed_layers

if __name__ == "__main__":
    try:
        success = clean_problematic_layers()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        sys.exit(1)
