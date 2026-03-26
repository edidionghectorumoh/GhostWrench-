#!/usr/bin/env python3
"""
Smoke Test for Autonomous Field Engineer System

Verifies critical system components after migration to Linux laptop:
1. Bedrock connectivity (Nova Pro, Claude 3.5 Sonnet)
2. Weaviate schema validation
3. Safe diagnosis test (no actual AWS calls)

Usage:
    python smoke_test.py
    python smoke_test.py --full  # Include actual Bedrock API calls
"""

import sys
import os
import argparse
from datetime import datetime
from typing import Dict, Any, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SmokeTest:
    """Smoke test suite for system verification."""
    
    def __init__(self, full_test: bool = False):
        """
        Initialize smoke test.
        
        Args:
            full_test: Run full tests including actual API calls
        """
        self.full_test = full_test
        self.results = []
    
    def run_all_tests(self) -> bool:
        """
        Run all smoke tests.
        
        Returns:
            True if all tests pass
        """
        print("\n" + "="*60)
        print("🔍 Autonomous Field Engineer - Smoke Test")
        print("="*60 + "\n")
        
        tests = [
            ("Environment Variables", self.test_environment_variables),
            ("Weaviate Connection", self.test_weaviate_connection),
            ("Weaviate Schema", self.test_weaviate_schema),
            ("AWS Credentials", self.test_aws_credentials),
        ]
        
        if self.full_test:
            tests.extend([
                ("Bedrock Nova Pro", self.test_bedrock_nova_pro),
                ("Bedrock Claude", self.test_bedrock_claude),
                ("Safe Diagnosis", self.test_safe_diagnosis),
            ])
        else:
            tests.append(("Configuration Check", self.test_configuration))
        
        all_passed = True
        
        for test_name, test_func in tests:
            print(f"\n📋 Testing: {test_name}")
            print("-" * 60)
            
            try:
                passed, message = test_func()
                
                if passed:
                    print(f"✅ PASS: {message}")
                    self.results.append((test_name, "PASS", message))
                else:
                    print(f"❌ FAIL: {message}")
                    self.results.append((test_name, "FAIL", message))
                    all_passed = False
                    
            except Exception as e:
                print(f"❌ ERROR: {str(e)}")
                self.results.append((test_name, "ERROR", str(e)))
                all_passed = False
        
        # Print summary
        self._print_summary(all_passed)
        
        return all_passed
    
    def test_environment_variables(self) -> Tuple[bool, str]:
        """Test required environment variables are set."""
        required_vars = [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_DEFAULT_REGION"
        ]
        
        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            return False, f"Missing environment variables: {', '.join(missing)}"
        
        region = os.getenv("AWS_DEFAULT_REGION")
        return True, f"All required variables set. Region: {region}"
    
    def test_weaviate_connection(self) -> Tuple[bool, str]:
        """Test Weaviate connection."""
        try:
            import requests
            
            weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
            
            response = requests.get(
                f"{weaviate_url}/v1/.well-known/ready",
                timeout=5
            )
            
            if response.status_code == 200:
                return True, f"Weaviate is ready at {weaviate_url}"
            else:
                return False, f"Weaviate returned status {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to Weaviate. Is it running?"
        except Exception as e:
            return False, f"Weaviate connection error: {str(e)}"
    
    def test_weaviate_schema(self) -> Tuple[bool, str]:
        """Test Weaviate schema is properly configured."""
        try:
            from src.rag.RAGSystem import RAGSystem
            
            weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
            rag = RAGSystem(weaviate_url=weaviate_url, use_titan_embeddings=False)
            
            # Check if schema exists
            schema_info = rag.get_schema_info()
            
            if schema_info.get("classes"):
                class_names = [c["class"] for c in schema_info["classes"]]
                return True, f"Schema configured with classes: {', '.join(class_names)}"
            else:
                return True, "Schema is empty but Weaviate is accessible"
                
        except Exception as e:
            return False, f"Schema validation error: {str(e)}"
    
    def test_aws_credentials(self) -> Tuple[bool, str]:
        """Test AWS credentials are valid."""
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
            
            # Try to get caller identity
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            
            account_id = identity.get('Account', 'unknown')
            user_id = identity.get('UserId', 'unknown')
            
            return True, f"AWS credentials valid. Account: {account_id}"
            
        except NoCredentialsError:
            return False, "AWS credentials not found"
        except ClientError as e:
            return False, f"AWS credentials invalid: {e.response['Error']['Message']}"
        except Exception as e:
            return False, f"AWS credential check error: {str(e)}"
    
    def test_bedrock_nova_pro(self) -> Tuple[bool, str]:
        """Test Bedrock Nova Pro access."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            bedrock = boto3.client(
                'bedrock-runtime',
                region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
            )
            
            # Try a minimal inference call
            response = bedrock.invoke_model(
                modelId='amazon.nova-pro-v1:0',
                body='{"messages":[{"role":"user","content":[{"text":"test"}]}],"inferenceConfig":{"max_new_tokens":10}}'
            )
            
            return True, "Nova Pro is accessible"
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':
                return False, "Nova Pro access denied. Check Bedrock model access in AWS console."
            else:
                return False, f"Nova Pro error: {e.response['Error']['Message']}"
        except Exception as e:
            return False, f"Nova Pro test error: {str(e)}"
    
    def test_bedrock_claude(self) -> Tuple[bool, str]:
        """Test Bedrock Claude 3.5 Sonnet access."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            bedrock = boto3.client(
                'bedrock-runtime',
                region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
            )
            
            # Try a minimal inference call
            response = bedrock.invoke_model(
                modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
                body='{"messages":[{"role":"user","content":"test"}],"max_tokens":10,"anthropic_version":"bedrock-2023-05-31"}'
            )
            
            return True, "Claude 3.5 Sonnet is accessible"
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':
                return False, "Claude access denied. Check Bedrock model access in AWS console."
            else:
                return False, f"Claude error: {e.response['Error']['Message']}"
        except Exception as e:
            return False, f"Claude test error: {str(e)}"
    
    def test_configuration(self) -> Tuple[bool, str]:
        """Test system configuration without API calls."""
        try:
            from src.orchestration.OrchestrationLayer import OrchestrationLayer
            
            # Initialize orchestration layer (no validation to avoid API calls)
            orchestration = OrchestrationLayer(enable_validation=False)
            
            return True, "System configuration is valid"
            
        except Exception as e:
            return False, f"Configuration error: {str(e)}"
    
    def test_safe_diagnosis(self) -> Tuple[bool, str]:
        """Test diagnosis workflow without actual AWS calls."""
        try:
            from src.orchestration.OrchestrationLayer import OrchestrationLayer
            from src.models.agents import FieldRequest, RequestType
            from src.models.domain import SiteContext
            
            # Initialize orchestration layer (no validation)
            orchestration = OrchestrationLayer(enable_validation=False)
            
            # Create minimal test request
            site_context = SiteContext(
                site_id="test-site-001",
                site_name="Test Site",
                site_type="data_center",
                location="Test Location",
                criticality_level="normal",
                operating_hours="24/7",
                environmental_conditions={"temperature": 20},
                component_id="test-component-001",
                component_type="network_switch"
            )
            
            request = FieldRequest(
                session_id="smoke-test-session",
                technician_id="smoke-test-tech",
                site_id="test-site-001",
                request_type=RequestType.DIAGNOSIS,
                site_context=site_context
            )
            
            # Test workflow initialization
            workflow_state = orchestration._initialize_workflow(
                "smoke-test-session",
                request
            )
            
            if workflow_state.session_id == "smoke-test-session":
                return True, "Diagnosis workflow initialization successful"
            else:
                return False, "Workflow state mismatch"
                
        except Exception as e:
            return False, f"Diagnosis test error: {str(e)}"
    
    def _print_summary(self, all_passed: bool):
        """Print test summary."""
        print("\n" + "="*60)
        print("📊 Test Summary")
        print("="*60 + "\n")
        
        passed_count = sum(1 for _, status, _ in self.results if status == "PASS")
        failed_count = sum(1 for _, status, _ in self.results if status in ["FAIL", "ERROR"])
        total_count = len(self.results)
        
        print(f"Total Tests: {total_count}")
        print(f"✅ Passed: {passed_count}")
        print(f"❌ Failed: {failed_count}")
        print()
        
        if all_passed:
            print("🎉 All tests passed! System is ready.")
        else:
            print("⚠️  Some tests failed. Review errors above.")
            print("\nFailed tests:")
            for test_name, status, message in self.results:
                if status in ["FAIL", "ERROR"]:
                    print(f"  - {test_name}: {message}")
        
        print("\n" + "="*60 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Smoke test for Autonomous Field Engineer system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick smoke test (no API calls)
  python smoke_test.py
  
  # Full smoke test (includes Bedrock API calls)
  python smoke_test.py --full
        """
    )
    
    parser.add_argument(
        '--full',
        action='store_true',
        help='Run full tests including actual Bedrock API calls'
    )
    
    args = parser.parse_args()
    
    try:
        smoke_test = SmokeTest(full_test=args.full)
        all_passed = smoke_test.run_all_tests()
        
        sys.exit(0 if all_passed else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
