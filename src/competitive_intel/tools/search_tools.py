"""LangGraph-compatible search tools for Competitive Intelligence."""

from typing import Any, ClassVar

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from competitive_intel.models import SearchEngine, SearchQuery, SearchResponse
from competitive_intel.tools.serpapi_tools import get_serpapi_tools


class WebSearchInput(BaseModel):
    """Input for web search."""

    query: str = Field(description="Search query string")
    engines: list[SearchEngine] | None = Field(default=None, description="Search engines to use")
    location: str | None = Field(default=None, description="Geographic location")
    num_results: int = Field(default=10, description="Number of results to return")
    date_range: str | None = Field(default=None, description="Date range filter (past_day, past_week, past_month, past_year)")


class WebSearchTool(BaseTool):
    """Web search tool for general research."""

    name: str = "web_search"
    description: str = "Search the web for current information, background research, and general knowledge."
    args_schema: type[BaseModel] = WebSearchInput
    response_format: str = "content_and_artifact"

    def _run(
        self,
        query: str,
        engines: list[SearchEngine] | None = None,
        location: str | None = None,
        num_results: int = 10,
        date_range: str | None = None,
    ) -> tuple[str, SearchResponse]:
        """Sync version - raises NotImplementedError as only async is supported."""
        raise NotImplementedError("Use async version _arun")

    def _run(
        self,
        *args,
        **kwargs,
    ) -> tuple[str, SearchResponse]:
        """Sync version not implemented."""
        raise NotImplementedError("Use async version _arun")

    async def _arun(
        self,
        query: str,
        engines: list[SearchEngine] | None = None,
        location: str | None = None,
        num_results: int = 10,
        date_range: str | None = None,
    ) -> tuple[str, SearchResponse]:
        tools = await get_serpapi_tools()
        search_query = SearchQuery(
            query=query,
            engines=engines or [SearchEngine.GOOGLE_LIGHT],
            location=location,
            num_results=num_results,
            date_range=date_range,
        )
        response = await tools.search(search_query, "web")
        return self._format_response(response), response

    def _format_response(self, response: SearchResponse) -> str:
        """Format response for LLM consumption."""
        if not response.results:
            return "No results found."

        lines = [f"Found {response.total_results} results in {response.search_time_ms:.0f}ms:"]
        for i, result in enumerate(response.results, 1):
            lines.append(f"\n{i}. **{result.title}**")
            lines.append(f"   URL: {result.url}")
            lines.append(f"   {result.snippet[:300]}...")
        return "\n".join(lines)


class NewsSearchInput(BaseModel):
    """Input for news search."""

    query: str = Field(description="News search query")
    location: str | None = Field(default=None, description="Geographic location")
    num_results: int = Field(default=20, description="Number of results")
    date_range: str | None = Field(default="past_week", description="Date range filter")


class NewsSearchTool(BaseTool):
    """News search tool for current events and reporting."""

    name: str = "news_search"
    description: str = "Search news sources for recent reporting, announcements, and current events."
    args_schema: type[BaseModel] = NewsSearchInput
    response_format: str = "content_and_artifact"

    def _run(
        self,
        *args,
        **kwargs,
    ) -> tuple[str, SearchResponse]:
        """Sync version not implemented."""
        raise NotImplementedError("Use async version _arun")

    async def _arun(
        self,
        query: str,
        location: str | None = None,
        num_results: int = 20,
        date_range: str | None = "past_week",
    ) -> tuple[str, SearchResponse]:
        tools = await get_serpapi_tools()
        search_query = SearchQuery(
            query=query,
            engines=[SearchEngine.GOOGLE_NEWS],
            location=location,
            num_results=num_results,
            date_range=date_range,
        )
        response = await tools.search(search_query, "news")
        return self._format_response(response), response

    def _format_response(self, response: SearchResponse) -> str:
        if not response.results:
            return "No news results found."

        lines = [f"Found {response.total_results} news articles:"]
        for i, result in enumerate(response.results, 1):
            lines.append(f"\n{i}. **{result.title}**")
            lines.append(f"   Source: {result.metadata.get('source', 'Unknown')}")
            lines.append(f"   Date: {result.metadata.get('date', 'Unknown')}")
            lines.append(f"   URL: {result.url}")
            lines.append(f"   {result.snippet[:300]}...")
        return "\n".join(lines)


class ShoppingSearchInput(BaseModel):
    """Input for shopping search."""

    query: str = Field(description="Product search query")
    engines: list[SearchEngine] | None = Field(default=None, description="Shopping engines")
    location: str | None = Field(default=None, description="Geographic location")
    num_results: int = Field(default=10, description="Number of results")


class ShoppingSearchTool(BaseTool):
    """Shopping search tool for product intelligence."""

    name: str = "shopping_search"
    description: str = "Search shopping platforms for product listings, prices, and availability."
    args_schema: type[BaseModel] = ShoppingSearchInput
    response_format: str = "content_and_artifact"

    def _run(
        self,
        *args,
        **kwargs,
    ) -> tuple[str, SearchResponse]:
        """Sync version not implemented."""
        raise NotImplementedError("Use async version _arun")

    async def _arun(
        self,
        query: str,
        engines: list[SearchEngine] | None = None,
        location: str | None = None,
        num_results: int = 10,
    ) -> tuple[str, SearchResponse]:
        tools = await get_serpapi_tools()
        search_query = SearchQuery(
            query=query,
            engines=engines or [SearchEngine.GOOGLE_SHOPPING, SearchEngine.AMAZON],
            location=location,
            num_results=num_results,
        )
        response = await tools.search(search_query, "shopping")
        return self._format_response(response), response

    def _format_response(self, response: SearchResponse) -> str:
        if not response.results:
            return "No shopping results found."

        lines = [f"Found {response.total_results} products:"]
        for i, result in enumerate(response.results, 1):
            price = result.metadata.get("price", "N/A")
            lines.append(f"\n{i}. **{result.title}** - {price}")
            lines.append(f"   Seller: {result.metadata.get('seller', 'Unknown')}")
            lines.append(f"   Rating: {result.metadata.get('rating', 'N/A')}")
            lines.append(f"   URL: {result.url}")
        return "\n".join(lines)


class MapsSearchInput(BaseModel):
    """Input for maps search."""

    query: str = Field(description="Place or business search query")
    location: str | None = Field(default=None, description="Geographic center for search")
    num_results: int = Field(default=10, description="Number of results")


class MapsSearchTool(BaseTool):
    """Maps search tool for local business intelligence."""

    name: str = "maps_search"
    description: str = "Search Google Maps for businesses, locations, and local intelligence."
    args_schema: type[BaseModel] = MapsSearchInput
    response_format: str = "content_and_artifact"

    def _run(
        self,
        *args,
        **kwargs,
    ) -> tuple[str, SearchResponse]:
        """Sync version not implemented."""
        raise NotImplementedError("Use async version _arun")

    async def _arun(
        self,
        query: str,
        location: str | None = None,
        num_results: int = 10,
    ) -> tuple[str, SearchResponse]:
        tools = await get_serpapi_tools()
        search_query = SearchQuery(
            query=query,
            engines=[SearchEngine.GOOGLE_MAPS],
            location=location,
            num_results=num_results,
        )
        response = await tools.search(search_query, "maps")
        return self._format_response(response), response

    def _format_response(self, response: SearchResponse) -> str:
        if not response.results:
            return "No maps results found."

        lines = [f"Found {response.total_results} places:"]
        for i, result in enumerate(response.results, 1):
            rating = result.metadata.get("rating", "N/A")
            reviews = result.metadata.get("reviews", "N/A")
            address = result.metadata.get("address", "Unknown")
            lines.append(f"\n{i}. **{result.title}** ⭐ {rating} ({reviews} reviews)")
            lines.append(f"   Address: {address}")
            lines.append(f"   Category: {result.metadata.get('category', 'Unknown')}")
            lines.append(f"   URL: {result.url}")
        return "\n".join(lines)


class ImagesSearchInput(BaseModel):
    """Input for image search."""

    query: str = Field(description="Image search query")
    num_results: int = Field(default=20, description="Number of results")


class ImagesSearchTool(BaseTool):
    """Image search tool for visual intelligence."""

    name: str = "images_search"
    description: str = "Search for images and visual content."
    args_schema: type[BaseModel] = ImagesSearchInput
    response_format: str = "content_and_artifact"

    def _run(
        self,
        *args,
        **kwargs,
    ) -> tuple[str, SearchResponse]:
        """Sync version not implemented."""
        raise NotImplementedError("Use async version _arun")

    async def _arun(
        self,
        query: str,
        num_results: int = 20,
    ) -> tuple[str, SearchResponse]:
        tools = await get_serpapi_tools()
        search_query = SearchQuery(
            query=query,
            engines=[SearchEngine.GOOGLE],
            num_results=num_results,
        )
        response = await tools.search(search_query, "images")
        return self._format_response(response), response

    def _format_response(self, response: SearchResponse) -> str:
        if not response.results:
            return "No image results found."

        lines = [f"Found {response.total_results} images:"]
        for i, result in enumerate(response.results, 1):
            lines.append(f"\n{i}. **{result.title}**")
            lines.append(f"   Source: {result.url}")
            lines.append(f"   Thumbnail: {result.metadata.get('thumbnail', 'N/A')}")
        return "\n".join(lines)


class VideosSearchInput(BaseModel):
    """Input for video search."""

    query: str = Field(description="Video search query")
    num_results: int = Field(default=10, description="Number of results")


class VideosSearchTool(BaseTool):
    """Video search tool for YouTube and video content."""

    name: str = "videos_search"
    description: str = "Search YouTube for videos, channels, and playlists."
    args_schema: type[BaseModel] = VideosSearchInput
    response_format: str = "content_and_artifact"

    def _run(
        self,
        *args,
        **kwargs,
    ) -> tuple[str, SearchResponse]:
        """Sync version not implemented."""
        raise NotImplementedError("Use async version _arun")

    async def _arun(
        self,
        query: str,
        num_results: int = 10,
    ) -> tuple[str, SearchResponse]:
        tools = await get_serpapi_tools()
        search_query = SearchQuery(
            query=query,
            engines=[SearchEngine.YOUTUBE],
            num_results=num_results,
        )
        response = await tools.search(search_query, "videos")
        return self._format_response(response), response

    def _format_response(self, response: SearchResponse) -> str:
        if not response.results:
            return "No video results found."

        lines = [f"Found {response.total_results} videos:"]
        for i, result in enumerate(response.results, 1):
            duration = result.metadata.get("duration", "N/A")
            channel = result.metadata.get("channel", "Unknown")
            views = result.metadata.get("views", "N/A")
            lines.append(f"\n{i}. **{result.title}**")
            lines.append(f"   Channel: {channel} | Duration: {duration} | Views: {views}")
            lines.append(f"   URL: {result.url}")
        return "\n".join(lines)


class FlightsSearchInput(BaseModel):
    """Input for flight search."""

    departure_id: str = Field(description="Departure airport code (e.g., JFK)")
    arrival_id: str = Field(description="Arrival airport code (e.g., LAX)")
    departure_date: str = Field(description="Departure date (YYYY-MM-DD)")
    return_date: str | None = Field(default=None, description="Return date for round trip (YYYY-MM-DD)")
    num_results: int = Field(default=10, description="Number of results")


class FlightsSearchTool(BaseTool):
    """Flight search tool for travel intelligence."""

    name: str = "flights_search"
    description: str = "Search Google Flights for routes, prices, and schedules."
    args_schema: type[BaseModel] = FlightsSearchInput
    response_format: str = "content_and_artifact"

    def _run(
        self,
        *args,
        **kwargs,
    ) -> tuple[str, SearchResponse]:
        """Sync version not implemented."""
        raise NotImplementedError("Use async version _arun")

    async def _arun(
        self,
        departure_id: str,
        arrival_id: str,
        departure_date: str,
        return_date: str | None = None,
        num_results: int = 10,
    ) -> tuple[str, SearchResponse]:
        tools = await get_serpapi_tools()
        query_str = f"{departure_id} to {arrival_id} on {departure_date}"
        if return_date:
            query_str += f" return {return_date}"

        search_query = SearchQuery(
            query=query_str,
            engines=[SearchEngine.GOOGLE_FLIGHTS],
            num_results=num_results,
        )
        response = await tools.search(search_query, "flights")
        return self._format_response(response), response

    def _format_response(self, response: SearchResponse) -> str:
        if not response.results:
            return "No flight results found."

        lines = [f"Found {response.total_results} flight options:"]
        for i, result in enumerate(response.results, 1):
            lines.append(f"\n{i}. **{result.title}**")
            lines.append(f"   {result.snippet}")
            lines.append(f"   URL: {result.url}")
        return "\n".join(lines)


class HotelsSearchInput(BaseModel):
    """Input for hotel search."""

    location: str = Field(description="Destination city or area")
    check_in: str = Field(description="Check-in date (YYYY-MM-DD)")
    check_out: str = Field(description="Check-out date (YYYY-MM-DD)")
    guests: int = Field(default=2, description="Number of guests")
    num_results: int = Field(default=10, description="Number of results")


class HotelsSearchTool(BaseTool):
    """Hotel search tool for accommodation intelligence."""

    name: str = "hotels_search"
    description: str = "Search Google Hotels for availability, prices, and amenities."
    args_schema: type[BaseModel] = HotelsSearchInput
    response_format: str = "content_and_artifact"

    def _run(
        self,
        *args,
        **kwargs,
    ) -> tuple[str, SearchResponse]:
        """Sync version not implemented."""
        raise NotImplementedError("Use async version _arun")

    async def _arun(
        self,
        location: str,
        check_in: str,
        check_out: str,
        guests: int = 2,
        num_results: int = 10,
    ) -> tuple[str, SearchResponse]:
        tools = await get_serpapi_tools()
        query_str = f"hotels in {location} check-in {check_in} check-out {check_out} guests {guests}"

        search_query = SearchQuery(
            query=query_str,
            engines=[SearchEngine.GOOGLE_HOTELS],
            num_results=num_results,
        )
        response = await tools.search(search_query, "hotels")
        return self._format_response(response), response

    def _format_response(self, response: SearchResponse) -> str:
        if not response.results:
            return "No hotel results found."

        lines = [f"Found {response.total_results} hotels:"]
        for i, result in enumerate(response.results, 1):
            price = result.metadata.get("price", "N/A")
            rating = result.metadata.get("rating", "N/A")
            lines.append(f"\n{i}. **{result.title}** - {price}/night ⭐ {rating}")
            lines.append(f"   {result.snippet}")
            lines.append(f"   URL: {result.url}")
        return "\n".join(lines)


class TravelExploreSearchInput(BaseModel):
    """Input for travel explore search."""

    departure_id: str = Field(description="Departure airport code")
    num_results: int = Field(default=20, description="Number of destinations")


class TravelExploreSearchTool(BaseTool):
    """Travel explore search for destination discovery."""

    name: str = "travel_explore_search"
    description: str = "Explore travel destinations from a departure point with indicative fares."
    args_schema: type[BaseModel] = TravelExploreSearchInput
    response_format: str = "content_and_artifact"

    def _run(
        self,
        *args,
        **kwargs,
    ) -> tuple[str, SearchResponse]:
        """Sync version not implemented."""
        raise NotImplementedError("Use async version _arun")

    async def _arun(
        self,
        departure_id: str,
        num_results: int = 20,
    ) -> tuple[str, SearchResponse]:
        tools = await get_serpapi_tools()
        query_str = f"destinations from {departure_id}"

        search_query = SearchQuery(
            query=query_str,
            engines=[SearchEngine.GOOGLE_FLIGHTS],
            num_results=num_results,
        )
        response = await tools.search(search_query, "travel_explore")
        return self._format_response(response), response

    def _format_response(self, response: SearchResponse) -> str:
        if not response.results:
            return "No destination results found."

        lines = [f"Found {response.total_results} destinations from {response.query.query}:"]
        for i, result in enumerate(response.results, 1):
            lines.append(f"\n{i}. **{result.title}**")
            lines.append(f"   {result.snippet}")
        return "\n".join(lines)


class SearchToolset:
    """Collection of all search tools for easy access."""

    def __init__(self) -> None:
        self.web = WebSearchTool()
        self.news = NewsSearchTool()
        self.shopping = ShoppingSearchTool()
        self.maps = MapsSearchTool()
        self.images = ImagesSearchTool()
        self.videos = VideosSearchTool()
        self.flights = FlightsSearchTool()
        self.hotels = HotelsSearchTool()
        self.travel_explore = TravelExploreSearchTool()

    def all_tools(self) -> list[BaseTool]:
        """Get all tools as a list."""
        return [
            self.web,
            self.news,
            self.shopping,
            self.maps,
            self.images,
            self.videos,
            self.flights,
            self.hotels,
            self.travel_explore,
        ]

    def intelligence_tools(self) -> list[BaseTool]:
        """Get tools optimized for competitive intelligence."""
        return [self.web, self.news, self.shopping, self.maps, self.videos]

    def travel_tools(self) -> list[BaseTool]:
        """Get tools optimized for travel planning."""
        return [self.flights, self.hotels, self.maps, self.travel_explore, self.web]


def create_search_toolset() -> SearchToolset:
    """Factory function to create a search toolset."""
    return SearchToolset()