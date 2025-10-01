"""
Search-related data models.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class SearchResult:
    """Search result data model."""
    title: str
    url: str
    snippet: Optional[str] = None
    site: Optional[str] = None
    score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'title': self.title,
            'url': self.url,
            'snippet': self.snippet,
            'site': self.site,
            'score': self.score,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchResult':
        """Create from dictionary."""
        return cls(
            title=data.get('title', ''),
            url=data.get('url', ''),
            snippet=data.get('snippet'),
            site=data.get('site'),
            score=data.get('score'),
            metadata=data.get('metadata', {})
        )


@dataclass
class SearchHistory:
    """Search history entry."""
    query: str
    timestamp: datetime
    results_count: int
    search_type: str = "general"
    filters: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'query': self.query,
            'timestamp': self.timestamp.isoformat(),
            'results_count': self.results_count,
            'search_type': self.search_type,
            'filters': self.filters
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchHistory':
        """Create from dictionary."""
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()
        
        return cls(
            id=data.get('id'),
            query=data.get('query', ''),
            timestamp=timestamp,
            results_count=data.get('results_count', 0),
            search_type=data.get('search_type', 'general'),
            filters=data.get('filters', {})
        )


@dataclass
class SearchFilter:
    """Search filter configuration."""
    name: str
    value: Any
    operator: str = "equals"  # equals, contains, greater_than, less_than, etc.
    
    def apply(self, item: Dict[str, Any]) -> bool:
        """
        Apply filter to an item.
        
        Args:
            item: Item to filter
            
        Returns:
            True if item passes filter
        """
        item_value = item.get(self.name)
        
        if item_value is None:
            return False
        
        if self.operator == "equals":
            return item_value == self.value
        elif self.operator == "contains":
            return str(self.value).lower() in str(item_value).lower()
        elif self.operator == "greater_than":
            return item_value > self.value
        elif self.operator == "less_than":
            return item_value < self.value
        elif self.operator == "starts_with":
            return str(item_value).lower().startswith(str(self.value).lower())
        elif self.operator == "ends_with":
            return str(item_value).lower().endswith(str(self.value).lower())
        else:
            return False


@dataclass
class SearchQuery:
    """Search query configuration."""
    text: str
    filters: List[SearchFilter] = field(default_factory=list)
    sort_by: Optional[str] = None
    sort_order: str = "desc"  # asc or desc
    limit: Optional[int] = None
    offset: int = 0
    
    def add_filter(self, name: str, value: Any, operator: str = "equals") -> None:
        """Add a filter to the query."""
        self.filters.append(SearchFilter(name, value, operator))
    
    def remove_filter(self, name: str) -> None:
        """Remove filters by name."""
        self.filters = [f for f in self.filters if f.name != name]
    
    def apply_filters(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply all filters to a list of items.
        
        Args:
            items: Items to filter
            
        Returns:
            Filtered items
        """
        filtered_items = items
        
        for filter_obj in self.filters:
            filtered_items = [item for item in filtered_items if filter_obj.apply(item)]
        
        return filtered_items
    
    def apply_sorting(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply sorting to items.
        
        Args:
            items: Items to sort
            
        Returns:
            Sorted items
        """
        if not self.sort_by:
            return items
        
        reverse = self.sort_order == "desc"
        
        try:
            return sorted(
                items,
                key=lambda x: x.get(self.sort_by, 0),
                reverse=reverse
            )
        except (TypeError, KeyError):
            return items
    
    def apply_pagination(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply pagination to items.
        
        Args:
            items: Items to paginate
            
        Returns:
            Paginated items
        """
        start = self.offset
        end = start + self.limit if self.limit else None
        
        return items[start:end]
    
    def execute(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute the complete query on items.
        
        Args:
            items: Items to query
            
        Returns:
            Query results
        """
        # Apply filters
        filtered_items = self.apply_filters(items)
        
        # Apply sorting
        sorted_items = self.apply_sorting(filtered_items)
        
        # Apply pagination
        paginated_items = self.apply_pagination(sorted_items)
        
        return paginated_items
