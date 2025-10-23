#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for hardware_detector_v2.py
Compatible with Python 2.7+ and 3.x
"""

from __future__ import print_function
import sys
import os
import json
import unittest
import tempfile
import shutil

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from detect_hardware_v2 import HardwareDetectorV2, run_cmd, which


class TestCommandRunner(unittest.TestCase):
    """Test the run_cmd utility function"""
    
    def test_run_cmd_success(self):
        """Test successful command execution"""
        rc, out, err = run_cmd(['echo', 'test'])
        self.assertEqual(rc, 0)
        self.assertEqual(out, 'test')
    
    def test_run_cmd_failure(self):
        """Test command failure handling"""
        rc, out, err = run_cmd(['false'])
        self.assertNotEqual(rc, 0)
    
    def test_run_cmd_nonexistent(self):
        """Test nonexistent command handling"""
        rc, out, err = run_cmd(['nonexistent_command_12345'])
        self.assertEqual(rc, -1)


class TestWhichFunction(unittest.TestCase):
    """Test the which() utility function"""
    
    def test_which_existing_command(self):
        """Test finding existing command"""
        # ls should exist on all Linux systems
        result = which('ls')
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
    
    def test_which_nonexistent_command(self):
        """Test handling of nonexistent command"""
        result = which('nonexistent_command_xyz_12345')
        self.assertIsNone(result)


class TestHardwareDetectorV2(unittest.TestCase):
    """Test the HardwareDetectorV2 class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = HardwareDetectorV2()
    
    def test_schema_version(self):
        """Test schema version is correct"""
        self.assertEqual(self.detector.SCHEMA_VERSION, '2.0')
        self.assertEqual(self.detector.info['schema_version'], '2.0')
    
    def test_required_top_level_keys(self):
        """Test all required top-level keys present"""
        required_keys = [
            'schema_version',
            'timestamp',
            'metadata',
            'system',
            'cpu',
            'numa',
            'gpu',
            'hwmon',
            'capabilities',
            'warnings'
        ]
        for key in required_keys:
            self.assertIn(key, self.detector.info,
                         msg="Missing required key: {}".format(key))
    
    def test_metadata_fields(self):
        """Test metadata section has required fields"""
        metadata = self.detector.info['metadata']
        required_fields = ['hostname', 'os', 'kernel', 'python_version']
        for field in required_fields:
            self.assertIn(field, metadata,
                         msg="Missing metadata field: {}".format(field))
            self.assertIsNotNone(metadata[field],
                               msg="Metadata field is None: {}".format(field))
    
    def test_cpu_vendor_detection(self):
        """Test CPU vendor is detected"""
        cpu = self.detector.info['cpu']
        self.assertIn('vendor', cpu)
        # Should be Intel, AMD, or ARM
        if cpu['vendor']:
            self.assertIn(cpu['vendor'], ['Intel', 'AMD', 'ARM', 'Unknown'])
    
    def test_cpu_structure(self):
        """Test CPU section has expected structure"""
        cpu = self.detector.info['cpu']
        # Check for key fields
        expected_fields = ['vendor', 'freq', 'rapl']
        for field in expected_fields:
            self.assertIn(field, cpu,
                         msg="Missing CPU field: {}".format(field))
    
    def test_amd_specific_fields(self):
        """Test AMD-specific fields when on AMD system"""
        cpu = self.detector.info['cpu']
        if cpu.get('vendor') == 'AMD':
            self.assertIn('amd_energy', cpu)
            self.assertIn('amd_uprof', cpu)
            
            # Check amd_energy structure
            amd_energy = cpu['amd_energy']
            self.assertIn('available', amd_energy)
            self.assertIn('readable', amd_energy)
            self.assertIn('sensors', amd_energy)
            self.assertIn('driver', amd_energy)
            
            # Check amd_uprof structure
            amd_uprof = cpu['amd_uprof']
            self.assertIn('installed', amd_uprof)
            self.assertIn('version', amd_uprof)
            self.assertIn('path', amd_uprof)
            self.assertIn('msr_available', amd_uprof)
            self.assertIn('capabilities', amd_uprof)
    
    def test_numa_detection(self):
        """Test NUMA detection structure"""
        numa = self.detector.info['numa']
        self.assertIsInstance(numa, dict)
        # Should have either data or a note about numactl
        if 'num_nodes' in numa:
            self.assertIsInstance(numa['num_nodes'], int)
            self.assertGreaterEqual(numa['num_nodes'], 1)
    
    def test_gpu_structure(self):
        """Test GPU section structure"""
        gpu = self.detector.info['gpu']
        self.assertIn('nvidia', gpu)
        self.assertIn('amd', gpu)
        self.assertIn('intel', gpu)
        self.assertIsInstance(gpu['nvidia'], list)
        self.assertIsInstance(gpu['amd'], list)
        self.assertIsInstance(gpu['intel'], list)
    
    def test_hwmon_structure(self):
        """Test hwmon section structure"""
        hwmon = self.detector.info['hwmon']
        self.assertIn('readable', hwmon)
        self.assertIn('sensors', hwmon)
        self.assertIsInstance(hwmon['sensors'], list)
    
    def test_capabilities_structure(self):
        """Test capabilities section"""
        caps = self.detector.info['capabilities']
        self.assertIn('tools', caps)
        self.assertIn('permissions', caps)
        
        # Check tool detection
        tools = caps['tools']
        expected_tools = [
            'perf', 'cpupower', 'turbostat', 'numactl',
            'nvidia-smi', 'rocm-smi', 'intel_gpu_top', 'ipmitool'
        ]
        for tool in expected_tools:
            self.assertIn(tool, tools)
            self.assertIsInstance(tools[tool], bool)
        
        # Check permissions
        perms = caps['permissions']
        self.assertIn('is_root', perms)
        self.assertIn('can_write_cpufreq', perms)
    
    def test_warnings_is_list(self):
        """Test warnings is a list"""
        warnings = self.detector.info['warnings']
        self.assertIsInstance(warnings, list)
    
    def test_json_serializable(self):
        """Test that info dict is JSON serializable"""
        try:
            json_str = json.dumps(self.detector.info)
            self.assertIsInstance(json_str, str)
        except Exception as e:
            self.fail("Info dict not JSON serializable: {}".format(e))
    
    def test_to_json_creates_file(self):
        """Test JSON file creation"""
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        try:
            output_path = os.path.join(temp_dir, 'test_output.json')
            result = self.detector.to_json(output_path)
            
            self.assertTrue(result, "to_json returned False")
            self.assertTrue(os.path.exists(output_path),
                          "JSON file was not created")
            
            # Verify JSON is valid
            with open(output_path, 'r') as f:
                data = json.load(f)
                self.assertEqual(data['schema_version'], '2.0')
        finally:
            shutil.rmtree(temp_dir)
    
    def test_print_report_runs(self):
        """Test that print_report executes without errors"""
        try:
            # Redirect stdout to avoid cluttering test output
            import io
            if sys.version_info[0] >= 3:
                from io import StringIO
            else:
                from StringIO import StringIO
            
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            
            self.detector.print_report()
            
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout
            
            # Check that some output was generated
            self.assertGreater(len(output), 0)
            self.assertIn('Proyecto10', output)
        except Exception as e:
            self.fail("print_report raised exception: {}".format(e))


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for realistic scenarios"""
    
    def test_full_detection_cycle(self):
        """Test complete detection cycle"""
        detector = HardwareDetectorV2()
        
        # Verify basic info is populated
        self.assertIsNotNone(detector.info['metadata']['hostname'])
        self.assertIsNotNone(detector.info['system']['arch'])
        
        # Check that at least some detection occurred
        cpu = detector.info['cpu']
        self.assertTrue(
            'vendor' in cpu or 'model' in cpu,
            "No CPU information detected"
        )
    
    def test_energy_monitoring_detection(self):
        """Test energy monitoring capability detection"""
        detector = HardwareDetectorV2()
        cpu = detector.info['cpu']
        caps = detector.info['capabilities']
        
        # Check RAPL or AMD energy is detected
        has_energy = (
            cpu.get('rapl', {}).get('available', False) or
            cpu.get('amd_energy', {}).get('available', False) or
            cpu.get('amd_uprof', {}).get('installed', False)
        )
        
        # On any reasonably modern system, some energy monitoring should be available
        # but we won't fail the test if not (could be VM or old hardware)
        if has_energy:
            print("Energy monitoring detected")
        else:
            print("Note: No energy monitoring detected (might be VM or old hardware)")


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""
    
    def test_handles_missing_tools_gracefully(self):
        """Test that missing tools don't crash detection"""
        detector = HardwareDetectorV2()
        # Should complete without exceptions even if tools are missing
        self.assertIsNotNone(detector.info)
    
    def test_handles_permission_errors_gracefully(self):
        """Test that permission errors are handled"""
        detector = HardwareDetectorV2()
        # Should complete without exceptions even with permission errors
        caps = detector.info['capabilities']
        # Permissions should be detected
        self.assertIn('permissions', caps)


def run_smoke_test():
    """Quick smoke test for manual verification"""
    print("="*60)
    print("SMOKE TEST: Hardware Detector v2")
    print("="*60)
    
    print("\n1. Creating detector instance...")
    detector = HardwareDetectorV2()
    
    print("2. Checking schema version...")
    assert detector.info['schema_version'] == '2.0', "Wrong schema version"
    print("   ✓ Schema version 2.0")
    
    print("3. Checking required sections...")
    required = ['metadata', 'system', 'cpu', 'numa', 'gpu', 'hwmon', 'capabilities', 'warnings']
    for section in required:
        assert section in detector.info, "Missing section: {}".format(section)
    print("   ✓ All required sections present")
    
    print("4. Checking CPU vendor...")
    vendor = detector.info['cpu'].get('vendor', 'Unknown')
    print("   ✓ CPU Vendor: {}".format(vendor))
    
    print("5. Checking energy monitoring...")
    if vendor == 'Intel':
        rapl = detector.info['cpu'].get('rapl', {})
        print("   ✓ RAPL available: {}".format(rapl.get('available', False)))
    elif vendor == 'AMD':
        amd_energy = detector.info['cpu'].get('amd_energy', {})
        amd_uprof = detector.info['cpu'].get('amd_uprof', {})
        print("   ✓ AMD Energy available: {}".format(amd_energy.get('available', False)))
        print("   ✓ AMD uProf installed: {}".format(amd_uprof.get('installed', False)))
    
    print("6. Testing JSON output...")
    temp_dir = tempfile.mkdtemp()
    try:
        json_path = os.path.join(temp_dir, 'test.json')
        detector.to_json(json_path)
        assert os.path.exists(json_path), "JSON file not created"
        with open(json_path, 'r') as f:
            data = json.load(f)
            assert data['schema_version'] == '2.0', "JSON validation failed"
        print("   ✓ JSON output valid")
    finally:
        shutil.rmtree(temp_dir)
    
    print("7. Testing console report...")
    detector.print_report()
    print("   ✓ Console report generated")
    
    print("\n" + "="*60)
    print("SMOKE TEST PASSED ✓")
    print("="*60)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test hardware detector')
    parser.add_argument('--smoke', action='store_true',
                       help='Run quick smoke test')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose test output')
    
    args = parser.parse_args()
    
    if args.smoke:
        run_smoke_test()
    else:
        # Run full test suite
        verbosity = 2 if args.verbose else 1
        unittest.main(argv=['test_detect_hardware.py'], verbosity=verbosity)
