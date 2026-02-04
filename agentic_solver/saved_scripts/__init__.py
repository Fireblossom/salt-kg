"""
Prediction Scripts for SALT-KG Target Fields

This module provides prediction functions for all target fields
defined in the SALT-KG paper.
"""

from .salesgroup import predict_salesgroup
from .salesorganization import predict_salesorganization
from .creationdate import predict_creationdate

__all__ = [
    'predict_salesgroup',
    'predict_salesorganization', 
    'predict_creationdate',
]