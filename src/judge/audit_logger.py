"""
Audit Logger for Local LLM Judge.

Maintains a local SQLite database of all validation judgments for compliance
and incident investigation. Supports offline operation with sync capability.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from ..models.validation import JudgmentResult, AgentOutput


logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Local audit logging system for judge validations.
    
    Stores all validation judgments in a local SQLite database with
    7-year retention for compliance requirements.
    """
    
    def __init__(self, db_path: str = "audit_logs/judgments.db"):
        """
        Initialize audit logger.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema
        self._init_database()
        
        logger.info(f"Audit logger initialized with database: {self.db_path}")
    
    def _init_database(self) -> None:
        """Initialize database schema if not exists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create judgments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS judgments (
                    judgment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    agent_type TEXT NOT NULL,
                    output_data TEXT,
                    validation_criteria TEXT,
                    approved INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    reasoning TEXT NOT NULL,
                    violations TEXT,
                    recommendations TEXT,
                    escalation_level TEXT,
                    requires_human_review INTEGER NOT NULL,
                    synced INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index on timestamp for efficient queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON judgments(timestamp)
            """)
            
            # Create index on session_id
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id 
                ON judgments(session_id)
            """)
            
            # Create index on synced status
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_synced 
                ON judgments(synced)
            """)
            
            conn.commit()
            logger.info("Database schema initialized successfully")
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def log_judgment(
        self,
        judgment: JudgmentResult,
        agent_output: Optional[AgentOutput] = None,
    ) -> int:
        """
        Log a judgment to the audit database.
        
        Args:
            judgment: Judgment result to log
            agent_output: Optional agent output that was judged
            
        Returns:
            Database row ID of the logged judgment
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Serialize complex objects to JSON
            violations_json = json.dumps([
                {
                    "type": v.violation_type.value,
                    "rule_id": v.rule_id,
                    "reason": v.reason,
                    "severity": v.severity,
                }
                for v in judgment.violations
            ])
            
            recommendations_json = json.dumps(judgment.recommendations)
            
            output_data_json = None
            session_id = None
            agent_type = "unknown"
            
            if agent_output:
                output_data_json = json.dumps(str(agent_output.output_data)[:1000])
                session_id = agent_output.session_id
                agent_type = agent_output.agent_type.value
            
            cursor.execute("""
                INSERT INTO judgments (
                    timestamp,
                    session_id,
                    agent_type,
                    output_data,
                    validation_criteria,
                    approved,
                    confidence,
                    reasoning,
                    violations,
                    recommendations,
                    escalation_level,
                    requires_human_review
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                judgment.timestamp.isoformat(),
                session_id,
                agent_type,
                output_data_json,
                None,  # validation_criteria - could be added if needed
                1 if judgment.approved else 0,
                judgment.confidence,
                judgment.reasoning,
                violations_json,
                recommendations_json,
                judgment.escalation_level.value,
                1 if judgment.requires_human_review else 0,
            ))
            
            conn.commit()
            judgment_id = cursor.lastrowid
            
            logger.info(
                f"Logged judgment {judgment_id}: "
                f"approved={judgment.approved}, "
                f"escalation={judgment.escalation_level.value}"
            )
            
            return judgment_id
    
    def get_judgment(self, judgment_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a judgment by ID.
        
        Args:
            judgment_id: Database row ID
            
        Returns:
            Judgment data as dictionary, or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM judgments WHERE judgment_id = ?",
                (judgment_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def get_judgments_for_session(
        self,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all judgments for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of judgment dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM judgments WHERE session_id = ? ORDER BY timestamp",
                (session_id,)
            )
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def get_unsynced_judgments(self) -> List[Dict[str, Any]]:
        """
        Retrieve all judgments that haven't been synced to central system.
        
        Returns:
            List of unsynced judgment dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM judgments WHERE synced = 0 ORDER BY timestamp"
            )
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def mark_synced(self, judgment_ids: List[int]) -> None:
        """
        Mark judgments as synced to central system.
        
        Args:
            judgment_ids: List of judgment IDs to mark as synced
        """
        if not judgment_ids:
            return
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(judgment_ids))
            cursor.execute(
                f"UPDATE judgments SET synced = 1 WHERE judgment_id IN ({placeholders})",
                judgment_ids
            )
            conn.commit()
            
            logger.info(f"Marked {len(judgment_ids)} judgments as synced")
    
    def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get validation statistics for compliance reporting.
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            Dictionary with validation statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build date filter
            date_filter = ""
            params = []
            if start_date:
                date_filter += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            if end_date:
                date_filter += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            # Total judgments
            cursor.execute(
                f"SELECT COUNT(*) as total FROM judgments WHERE 1=1 {date_filter}",
                params
            )
            total = cursor.fetchone()['total']
            
            # Approved vs rejected
            cursor.execute(
                f"SELECT approved, COUNT(*) as count FROM judgments WHERE 1=1 {date_filter} GROUP BY approved",
                params
            )
            approval_stats = {row['approved']: row['count'] for row in cursor.fetchall()}
            
            # Escalation frequency
            cursor.execute(
                f"SELECT escalation_level, COUNT(*) as count FROM judgments WHERE 1=1 {date_filter} GROUP BY escalation_level",
                params
            )
            escalation_stats = {row['escalation_level']: row['count'] for row in cursor.fetchall()}
            
            # Safety violations
            cursor.execute(
                f"SELECT COUNT(*) as count FROM judgments WHERE violations LIKE '%safety%' {date_filter}",
                params
            )
            safety_violations = cursor.fetchone()['count']
            
            return {
                "total_judgments": total,
                "approved": approval_stats.get(1, 0),
                "rejected": approval_stats.get(0, 0),
                "approval_rate": approval_stats.get(1, 0) / total if total > 0 else 0,
                "escalations": escalation_stats,
                "safety_violations": safety_violations,
            }
    
    def cleanup_old_records(self, retention_years: int = 7) -> int:
        """
        Clean up records older than retention period.
        
        Args:
            retention_years: Number of years to retain records (default: 7 for compliance)
            
        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.now().replace(year=datetime.now().year - retention_years)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM judgments WHERE timestamp < ?",
                (cutoff_date.isoformat(),)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"Cleaned up {deleted_count} records older than {retention_years} years")
            
            return deleted_count
    
    def sync_to_central_system(
        self,
        central_api_url: str,
        api_key: str,
    ) -> int:
        """
        Sync unsynced judgments to central system.
        
        Args:
            central_api_url: URL of central audit system API
            api_key: API key for authentication
            
        Returns:
            Number of judgments successfully synced
        """
        import requests
        
        unsynced = self.get_unsynced_judgments()
        
        if not unsynced:
            logger.info("No unsynced judgments to sync")
            return 0
        
        synced_ids = []
        
        for judgment in unsynced:
            try:
                response = requests.post(
                    f"{central_api_url}/audit/judgments",
                    json=judgment,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10,
                )
                response.raise_for_status()
                synced_ids.append(judgment['judgment_id'])
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to sync judgment {judgment['judgment_id']}: {e}")
                # Continue with other judgments
        
        if synced_ids:
            self.mark_synced(synced_ids)
        
        logger.info(f"Successfully synced {len(synced_ids)} of {len(unsynced)} judgments")
        
        return len(synced_ids)
