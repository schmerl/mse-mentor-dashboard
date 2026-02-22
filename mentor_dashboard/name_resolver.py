"""Name resolution module for mapping Andrew IDs to formatted names."""

import pandas as pd
import re
from typing import Dict, Optional


class NameResolver:
    """Resolves names from roster data to display proper 'First Last' format."""
    
    def __init__(self, roster_path: str):
        """Initialize name resolver with roster CSV file.
        
        Args:
            roster_path: Path to roster.csv file
        """
        self.roster_df = pd.read_csv(roster_path)
        self._name_mapping: Optional[Dict[str, str]] = None
        self._build_name_mapping()
    
    def _build_name_mapping(self) -> None:
        """Build mapping from Andrew IDs to formatted names."""
        self._name_mapping = {}
        
        for _, row in self.roster_df.iterrows():
            # Extract Andrew ID from email
            email = str(row.get('Email', ''))
            andrew_id_match = re.match(r'([^@]+)@andrew\.cmu\.edu', email)
            if andrew_id_match:
                andrew_id = andrew_id_match.group(1)
                
                # Format name as "First Last"
                first_name = str(row.get('Preferred/First Name', '')).strip()
                last_name = str(row.get('Last Name', '')).strip()
                
                if first_name and last_name:
                    formatted_name = f"{first_name} {last_name}"
                    self._name_mapping[andrew_id.lower()] = formatted_name
                    
                    # Also map the Andrew ID directly
                    self._name_mapping[str(row.get('Andrew ID', '')).lower()] = formatted_name
    
    def resolve_name(self, user_field: str, email_field: str = '') -> str:
        """Resolve a name from user field and email to proper format.
        
        Args:
            user_field: Content of the 'User' field from time tracking CSV
            email_field: Content of the 'Email' field from time tracking CSV
            
        Returns:
            Properly formatted "First Last" name, or original user_field if not found
        """
        if not self._name_mapping:
            return user_field
        
        # Clean up the user field
        user_clean = str(user_field).strip()
        
        # First try: check if user_field is already a full name format
        if ' ' in user_clean and len(user_clean.split()) >= 2:
            # Check if this matches any of our resolved names
            for andrew_id, formatted_name in self._name_mapping.items():
                if formatted_name.lower() == user_clean.lower():
                    return formatted_name
            # If it looks like a proper name but not in roster, return as-is
            return user_clean
        
        # Second try: treat user_field as Andrew ID
        andrew_id_from_user = user_clean.lower()
        if andrew_id_from_user in self._name_mapping:
            return self._name_mapping[andrew_id_from_user]
        
        # Third try: extract Andrew ID from email field
        if email_field:
            email_match = re.match(r'([^@]+)@andrew\.cmu\.edu', str(email_field))
            if email_match:
                andrew_id_from_email = email_match.group(1).lower()
                if andrew_id_from_email in self._name_mapping:
                    return self._name_mapping[andrew_id_from_email]
        
        # Fallback: return original user field
        return user_clean
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the name resolver.
        
        Returns:
            Dictionary with statistics about resolved names
        """
        return {
            'total_names_in_roster': len(self._name_mapping) if self._name_mapping else 0,
            'roster_entries': len(self.roster_df)
        }