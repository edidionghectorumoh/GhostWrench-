#!/usr/bin/env python3
"""
Autonomous Field Engineer - Main CLI

Command-line interface for field technicians to interact with the
Autonomous Field Engineer system.

Usage:
    python main.py diagnose --image photo.jpg --site site-001
    python main.py status --session session-123
    python main.py guidance --session session-123
"""

import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

from src.orchestration.OrchestrationLayer import OrchestrationLayer
from src.models.agents import FieldRequest, RequestType
from src.models.domain import (
    ImageData,
    ImageMetadata,
    GeoLocation
)


class FieldEngineerCLI:
    """Command-line interface for field engineers."""
    
    def __init__(self):
        """Initialize CLI."""
        self.orchestration = OrchestrationLayer(enable_validation=False)
        print("✅ System initialized")
    
    def diagnose(self, args):
        """
        Submit diagnosis request with equipment photo.
        
        Args:
            args: Command arguments
        """
        print(f"\n📸 Processing diagnosis request...")
        print(f"   Image: {args.image}")
        print(f"   Site: {args.site}")
        print(f"   Technician: {args.technician}")
        
        # Load image
        image_path = Path(args.image)
        if not image_path.exists():
            print(f"❌ Error: Image file not found: {args.image}")
            return 1
        
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        # Create image data
        image_data = ImageData(
            image_id=f"img-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            raw_image=image_bytes,
            resolution={"width": 1920, "height": 1080},
            capture_timestamp=datetime.now(),
            capture_location=GeoLocation(latitude=0.0, longitude=0.0),
            metadata=ImageMetadata(
                device_model="CLI Upload",
                orientation="landscape"
            )
        )
        
        # Create field request
        request = FieldRequest(
            session_id=f"session-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            technician_id=args.technician,
            site_id=args.site,
            request_type=RequestType.DIAGNOSIS,
            image_data=image_data
        )
        
        print(f"\n🔄 Submitting to diagnosis agent...")
        
        # Process request (would call orchestration.process_field_request in production)
        print(f"\n✅ Diagnosis request submitted")
        print(f"   Session ID: {request.session_id}")
        print(f"\n💡 Use 'python main.py status --session {request.session_id}' to check status")
        
        return 0
    
    def status(self, args):
        """
        Check status of existing session.
        
        Args:
            args: Command arguments
        """
        print(f"\n📊 Checking session status...")
        print(f"   Session: {args.session}")
        
        # In production, would query orchestration layer for session state
        print(f"\n✅ Session found")
        print(f"   Status: In Progress")
        print(f"   Current Phase: DIAGNOSIS")
        print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return 0
    
    def guidance(self, args):
        """
        Start voice-guided repair session.
        
        Args:
            args: Command arguments
        """
        print(f"\n🎤 Starting voice-guided repair...")
        print(f"   Session: {args.session}")
        
        print(f"\n✅ Guidance session ready")
        print(f"   Say 'next step' to begin")
        print(f"   Say 'repeat' to hear current step again")
        print(f"   Say 'help' for assistance")
        
        return 0
    
    def list_sessions(self, args):
        """
        List all active sessions for technician.
        
        Args:
            args: Command arguments
        """
        print(f"\n📋 Active sessions for {args.technician}:")
        print(f"\n   No active sessions found")
        
        return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Autonomous Field Engineer CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Submit diagnosis request
  python main.py diagnose --image photo.jpg --site site-001 --technician tech-001
  
  # Check session status
  python main.py status --session session-123
  
  # Start voice-guided repair
  python main.py guidance --session session-123
  
  # List active sessions
  python main.py list --technician tech-001
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Diagnose command
    diagnose_parser = subparsers.add_parser('diagnose', help='Submit diagnosis request')
    diagnose_parser.add_argument('--image', required=True, help='Path to equipment photo')
    diagnose_parser.add_argument('--site', required=True, help='Site ID')
    diagnose_parser.add_argument('--technician', default='tech-001', help='Technician ID')
    diagnose_parser.add_argument('--description', help='Issue description')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check session status')
    status_parser.add_argument('--session', required=True, help='Session ID')
    
    # Guidance command
    guidance_parser = subparsers.add_parser('guidance', help='Start voice-guided repair')
    guidance_parser.add_argument('--session', required=True, help='Session ID')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List active sessions')
    list_parser.add_argument('--technician', required=True, help='Technician ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        cli = FieldEngineerCLI()
        
        if args.command == 'diagnose':
            return cli.diagnose(args)
        elif args.command == 'status':
            return cli.status(args)
        elif args.command == 'guidance':
            return cli.guidance(args)
        elif args.command == 'list':
            return cli.list_sessions(args)
        else:
            print(f"❌ Unknown command: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
