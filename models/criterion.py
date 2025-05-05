# models/criterion.py
import streamlit as st

class Criterion:
    """
    Class representing a criterion for suitability analysis.
    """
    
    def __init__(self, id, name, data_source, processing_method, column=None, weight=0.5, preference='Higher is better'):
        """
        Initialize a criterion.
        
        Args:
            id (str): Unique identifier for the criterion
            name (str): Name of the criterion
            data_source (str): Name of the dataset to use
            processing_method (str): Method to process the data
            column (str, optional): Column to use from the dataset
            weight (float): Weight of the criterion (0-1)
            preference (str): Whether higher or lower values are preferred
        """
        self.id = id
        self.name = name
        self.data_source = data_source
        self.processing_method = processing_method
        self.column = column
        self.weight = weight
        self.preference = preference
        
    def to_dict(self):
        """Convert the criterion to a dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'data_source': self.data_source,
            'processing_method': self.processing_method,
            'column': self.column,
            'weight': self.weight,
            'preference': self.preference
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a criterion from a dictionary."""
        return cls(
            id=data['id'],
            name=data['name'],
            data_source=data['data_source'],
            processing_method=data['processing_method'],
            column=data.get('column'),
            weight=data.get('weight', 0.5),
            preference=data.get('preference', 'Higher is better')
        )
    
    def display_info(self):
        """Display criterion information in Streamlit."""
        st.write(f"**Name:** {self.name}")
        st.write(f"**Data Source:** {self.data_source}")
        st.write(f"**Processing Method:** {self.processing_method}")
        if self.column:
            st.write(f"**Column:** {self.column}")
        st.write(f"**Weight:** {self.weight}")
        st.write(f"**Preference:** {self.preference}")