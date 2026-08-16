"""Load and validate the central assumptions file."""

import yaml
import os
from pathlib import Path


class Assumptions:
    """Accessor for assumptions.yaml values.
    
    Usage:
        config = Assumptions()
        pop = config.get('demographics.urban_population')  # returns the 'value' field
        low, high = config.get_range('order_economics.tier1_orders_per_hh_per_month')
    """
    
    def __init__(self, path=None):
        if path is None:
            path = Path(__file__).parent.parent / 'assumptions.yaml'
        with open(path, 'r') as f:
            self._data = yaml.safe_load(f)
    
    def get(self, dotted_key):
        """Get the 'value' field for a dotted key like 'demographics.urban_population'.
        If the resolved object is a dict with a 'value' key, return that.
        Otherwise return the object itself (for simple scalar keys).
        """
        obj = self._resolve(dotted_key)
        if isinstance(obj, dict) and 'value' in obj:
            return obj['value']
        return obj
    
    def get_range(self, dotted_key):
        """Return (low, base, high) for an assumption that has low/high fields."""
        obj = self._resolve(dotted_key)
        if not isinstance(obj, dict):
            raise KeyError(f"Key '{dotted_key}' is not a dict, cannot get range")
        base = obj.get('value')
        low = obj.get('low', base)
        high = obj.get('high', base)
        return low, base, high
    
    def get_source(self, dotted_key):
        """Return the source citation for an assumption."""
        obj = self._resolve(dotted_key)
        if isinstance(obj, dict):
            return obj.get('source', 'No source specified')
        return 'No source specified'
    
    def is_assumption(self, dotted_key):
        """Return whether this parameter is an assumption (True) or a filed/sourced figure (False)."""
        obj = self._resolve(dotted_key)
        if isinstance(obj, dict):
            return obj.get('is_assumption', True)
        return False
    
    def _resolve(self, dotted_key):
        parts = dotted_key.split('.')
        obj = self._data
        for part in parts:
            if isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                raise KeyError(f"Key '{dotted_key}' not found (failed at '{part}')")
        return obj
    
    @property
    def raw(self):
        return self._data
