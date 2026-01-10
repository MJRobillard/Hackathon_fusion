#!/usr/bin/env python3
"""
Master script to run all OpenMC verification studies sequentially
==================================================================

This script executes all five verification studies in order and generates
a comprehensive summary report.

Usage:
------
    python run_all_studies.py [--skip N] [--only N]

Options:
    --skip N    : Skip study number N
    --only N    : Run only study number N
    --quick     : Use reduced particle counts for faster verification

Example:
    python run_all_studies.py                    # Run all studies
    python run_all_studies.py --skip 4           # Skip study 4
    python run_all_studies.py --only 3           # Run only study 3
    python run_all_studies.py --quick            # Quick verification mode
"""

import sys
import os
import time
import argparse
from datetime import datetime
import importlib.util


class VerificationRunner:
    """Manages execution of all verification studies"""
    
    STUDIES = [
        {
            'number': 1,
            'name': '01_toy_geometry',
            'title': 'Two-Volume Toy Geometry',
            'description': 'Basic OpenMC functionality test',
            'expected_time': '1-2 minutes'
        },
        {
            'number': 2,
            'name': '02_single_torus',
            'title': 'Single Layered Torus',
            'description': 'Toroidal geometry and ring sources',
            'expected_time': '5-10 minutes'
        },
        {
            'number': 3,
            'name': '03_multi_torus',
            'title': 'Multi-Layered Torus',
            'description': 'Tritium breeding calculations',
            'expected_time': '10-15 minutes'
        },
        {
            'number': 4,
            'name': '04_reactor_model',
            'title': 'DEMO Reactor Model',
            'description': 'Full-scale integral parameters',
            'expected_time': '15-30 minutes'
        },
        {
            'number': 5,
            'name': '05_sector_model',
            'title': 'Sector Slicing Model',
            'description': 'Computational efficiency demonstration',
            'expected_time': '5-10 minutes'
        }
    ]
    
    def __init__(self):
        self.results = []
        self.start_time = None
        self.total_time = 0
    
    def print_header(self):
        """Print welcome header"""
        print("\n" + "="*80)
        print("OpenMC VERIFICATION SUITE")
        print("="*80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total studies: {len(self.STUDIES)}")
        print(f"Estimated total time: 40-70 minutes")
        print("="*80 + "\n")
    
    def print_study_header(self, study):
        """Print header for individual study"""
        print("\n" + "▓"*80)
        print(f"▓ STUDY {study['number']}: {study['title']}")
        print("▓"*80)
        print(f"Description : {study['description']}")
        print(f"Expected time: {study['expected_time']}")
        print(f"Script       : {study['name']}.py")
        print("▓"*80 + "\n")
    
    def run_study(self, study):
        """
        Run a single verification study
        
        Returns:
            tuple: (success: bool, runtime: float, error_message: str)
        """
        study_file = f"{study['name']}.py"
        
        if not os.path.exists(study_file):
            return False, 0.0, f"Study file {study_file} not found"
        
        # Import and run the study module
        try:
            # Load module dynamically
            spec = importlib.util.spec_from_file_location(study['name'], study_file)
            module = importlib.util.module_from_spec(spec)
            
            study_start = time.time()
            
            # Execute the module (runs the study)
            spec.loader.exec_module(module)
            
            # The module's __main__ block should have run
            # Most studies have a run_study() function that returns (success, runtime)
            if hasattr(module, 'run_study'):
                success, runtime = module.run_study()
            else:
                # If no run_study function, assume success if no exception
                runtime = time.time() - study_start
                success = True
            
            return success, runtime, None
            
        except Exception as e:
            runtime = time.time() - study_start
            error_msg = f"{type(e).__name__}: {str(e)}"
            return False, runtime, error_msg
    
    def run_all(self, skip_studies=None, only_study=None):
        """
        Run all verification studies
        
        Args:
            skip_studies (list): List of study numbers to skip
            only_study (int): Run only this study number
        """
        self.start_time = time.time()
        self.results = []
        
        skip_studies = skip_studies or []
        
        # Filter studies
        studies_to_run = self.STUDIES
        if only_study:
            studies_to_run = [s for s in self.STUDIES if s['number'] == only_study]
            if not studies_to_run:
                print(f"❌ Study {only_study} not found!")
                return
        else:
            studies_to_run = [s for s in self.STUDIES if s['number'] not in skip_studies]
        
        # Print header
        self.print_header()
        
        if skip_studies:
            print(f"ℹ️  Skipping studies: {skip_studies}\n")
        
        # Run each study
        for idx, study in enumerate(studies_to_run, 1):
            self.print_study_header(study)
            
            success, runtime, error = self.run_study(study)
            
            result = {
                'study': study,
                'success': success,
                'runtime': runtime,
                'error': error
            }
            self.results.append(result)
            
            # Print immediate result
            if success:
                print(f"\n✅ Study {study['number']} PASSED")
                print(f"   Runtime: {runtime:.2f} seconds ({runtime/60:.2f} minutes)")
            else:
                print(f"\n❌ Study {study['number']} FAILED")
                print(f"   Runtime: {runtime:.2f} seconds")
                if error:
                    print(f"   Error: {error}")
                
                # Ask if user wants to continue
                if idx < len(studies_to_run):
                    response = input("\nContinue with remaining studies? (y/n): ")
                    if response.lower() != 'y':
                        print("Stopping verification suite.")
                        break
        
        self.total_time = time.time() - self.start_time
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print final summary report"""
        print("\n\n" + "="*80)
        print("VERIFICATION SUITE SUMMARY")
        print("="*80)
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total time: {self.total_time:.2f} seconds ({self.total_time/60:.2f} minutes)")
        print("-"*80)
        
        # Results table
        print(f"\n{'#':<4} {'Study':<35} {'Status':<10} {'Time (min)':<12}")
        print("-"*80)
        
        passed_count = 0
        for result in self.results:
            study = result['study']
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            runtime_min = result['runtime'] / 60
            
            print(f"{study['number']:<4} {study['title']:<35} {status:<10} {runtime_min:>8.2f}")
            
            if result['success']:
                passed_count += 1
        
        print("-"*80)
        print(f"Results: {passed_count}/{len(self.results)} studies passed")
        
        # Overall verdict
        print("\n" + "="*80)
        if passed_count == len(self.results):
            print("🎉 ALL VERIFICATION STUDIES PASSED! 🎉")
            print("="*80)
            print("\nYour OpenMC installation is fully verified and ready for:")
            print("  ✓ Production fusion neutronics calculations")
            print("  ✓ Reactor design optimization")
            print("  ✓ Research-grade simulations")
            print("  ✓ Integration with AONP automated workflow")
            print("\nNext steps:")
            print("  1. Review individual study outputs in *_output/ directories")
            print("  2. Increase particle counts for production runs")
            print("  3. Explore parameter variations")
            print("  4. Integrate with AONP framework")
        else:
            print("⚠️  SOME STUDIES FAILED")
            print("="*80)
            print("\nFailed studies:")
            for result in self.results:
                if not result['success']:
                    study = result['study']
                    print(f"  • Study {study['number']}: {study['title']}")
                    if result['error']:
                        print(f"    Error: {result['error']}")
            
            print("\nTroubleshooting:")
            print("  1. Check nuclear data library configuration")
            print("  2. Verify OpenMC installation (openmc --version)")
            print("  3. Review individual study output files")
            print("  4. Consult README.md for common issues")
        
        print("="*80 + "\n")
    
    def save_report(self, filename='verification_report.txt'):
        """Save detailed report to file"""
        with open(filename, 'w') as f:
            f.write("="*80 + "\n")
            f.write("OpenMC Verification Suite Report\n")
            f.write("="*80 + "\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total runtime: {self.total_time:.2f} seconds\n")
            f.write("\n")
            
            for result in self.results:
                study = result['study']
                f.write(f"\nStudy {study['number']}: {study['title']}\n")
                f.write("-"*80 + "\n")
                f.write(f"Status: {'PASSED' if result['success'] else 'FAILED'}\n")
                f.write(f"Runtime: {result['runtime']:.2f} seconds\n")
                if result['error']:
                    f.write(f"Error: {result['error']}\n")
                f.write("\n")
        
        print(f"📄 Detailed report saved to: {filename}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Run OpenMC verification studies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--skip',
        type=int,
        action='append',
        metavar='N',
        help='Skip study number N (can be used multiple times)'
    )
    
    parser.add_argument(
        '--only',
        type=int,
        metavar='N',
        help='Run only study number N'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick mode: use reduced particle counts (not implemented yet)'
    )
    
    parser.add_argument(
        '--report',
        type=str,
        default='verification_report.txt',
        help='Output report filename (default: verification_report.txt)'
    )
    
    args = parser.parse_args()
    
    # Create runner
    runner = VerificationRunner()
    
    # Run studies
    runner.run_all(skip_studies=args.skip, only_study=args.only)
    
    # Save report
    runner.save_report(args.report)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Verification interrupted by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

