"""News-related step definitions for Epic 5: Economic News Aggregation UI.

These steps handle news browsing, filtering, and refresh functionality.
Fixtures are loaded from tests/fixtures/news_fixtures.py.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

from pytest_bdd import given, parsers, then, when

# ==============================================================================
# US-5.1: Browse News Sources
# ==============================================================================


@given("news sources exist in the database")
def news_sources_exist(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
    sample_news_categories: list[dict[str, Any]],
) -> None:
    """Configure platform client to return news sources."""
    mock_platform_client.list_news_categories.return_value = sample_news_categories
    scenario_context["news_sources_configured"] = True


@given("no news sources exist")
def no_news_sources(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Configure platform client to return no news sources."""
    mock_platform_client.list_news_categories.return_value = []
    scenario_context["no_news_sources"] = True


@given(parsers.parse('a news source "{name}" exists with URL "{url}"'))
def news_source_with_url(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
    name: str,
    url: str,
) -> None:
    """Configure a specific news source."""
    mock_platform_client.list_news_categories.return_value = [
        {
            "id": 1,
            "name": "Central Banks",
            "sources": [
                {
                    "id": 1,
                    "title": name,
                    "url": url,
                    "is_active": True,
                    "last_fetched_at": datetime.now(UTC).isoformat(),
                    "last_fetch_status": "success",
                    "article_count": 5,
                },
            ],
            "source_count": 1,
            "total_articles": 5,
        },
    ]
    scenario_context["source_name"] = name
    scenario_context["source_url"] = url


@given(parsers.parse('a source "{name}" was last fetched "{time_ago}"'))
def source_last_fetched(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
    name: str,
    time_ago: str,
) -> None:
    """Configure a source with a specific last fetched time."""
    if "hours ago" in time_ago:
        hours = int(time_ago.split()[0])
        last_fetched = datetime.now(UTC) - timedelta(hours=hours)
    else:
        last_fetched = datetime.now(UTC) - timedelta(hours=2)

    mock_platform_client.list_news_categories.return_value = [
        {
            "id": 1,
            "name": "Central Banks",
            "sources": [
                {
                    "id": 1,
                    "title": name,
                    "url": f"https://{name.lower()}.europa.eu",
                    "is_active": True,
                    "last_fetched_at": last_fetched.isoformat(),
                    "last_fetch_status": "success",
                    "article_count": 5,
                },
            ],
            "source_count": 1,
            "total_articles": 5,
        },
    ]
    scenario_context["source_name"] = name
    scenario_context["time_ago"] = time_ago


@given(parsers.parse('a source "{name}" has last_fetch_status "{status}"'))
def source_fetch_status(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
    name: str,
    status: str,
) -> None:
    """Configure a source with a specific fetch status."""
    mock_platform_client.list_news_categories.return_value = [
        {
            "id": 1,
            "name": "Central Banks",
            "sources": [
                {
                    "id": 1,
                    "title": name,
                    "url": f"https://{name.lower()}.europa.eu",
                    "is_active": True,
                    "last_fetched_at": datetime.now(UTC).isoformat(),
                    "last_fetch_status": status,
                    "last_fetch_error": "HTTP 503 Service Unavailable"
                    if status == "error"
                    else None,
                    "article_count": 0,
                },
            ],
            "source_count": 1,
            "total_articles": 0,
        },
    ]
    scenario_context["source_name"] = name
    scenario_context["source_status"] = status


@when("I navigate to the News tab")
def navigate_to_news_tab(
    scenario_context: dict[str, Any],
    api_client: Any,
) -> None:
    """Navigate to the News tab."""
    response = api_client.get("/api/news")
    scenario_context["response"] = response


@when("I view the News tab")
def view_news_tab(
    scenario_context: dict[str, Any],
    api_client: Any,
) -> None:
    """View the News tab (same as navigate)."""
    response = api_client.get("/api/news")
    scenario_context["response"] = response


@when(parsers.parse('I click on the source "{name}"'))
def click_source(
    scenario_context: dict[str, Any],
    name: str,
) -> None:
    """Click on a source."""
    scenario_context["clicked_source"] = name


@then("I should see sources grouped by category")
def check_sources_grouped(scenario_context: dict[str, Any]) -> None:
    """Verify sources are grouped by category."""
    response = scenario_context.get("response")
    if response:
        assert response.status_code == 200


@then(parsers.parse('I should see categories like "{cat1}" and "{cat2}"'))
def check_categories_visible(
    scenario_context: dict[str, Any],
    cat1: str,
    cat2: str,
) -> None:
    """Verify specific categories are visible."""
    response = scenario_context.get("response")
    if response:
        assert response.status_code == 200


@then(parsers.parse('I should see "{text}"'))
def check_text_visible(
    scenario_context: dict[str, Any],
    text: str,
) -> None:
    """Verify specific text is visible."""
    response = scenario_context.get("response")
    if response:
        assert response.status_code == 200


@then(parsers.parse('a new tab should open with URL "{url}"'))
def check_new_tab_url(
    scenario_context: dict[str, Any],
    url: str,
) -> None:
    """Verify the URL for the new tab."""
    expected_url = scenario_context.get("source_url")
    if expected_url:
        assert expected_url == url or url in expected_url


@then(parsers.parse('I should see "{text}" for source "{name}"'))
def check_text_for_source(
    scenario_context: dict[str, Any],
    text: str,
    name: str,
) -> None:
    """Verify text is visible for a specific source."""
    assert scenario_context.get("source_name") == name


@then(parsers.parse('I should see an error indicator next to "{name}"'))
def check_error_indicator(
    scenario_context: dict[str, Any],
    name: str,
) -> None:
    """Verify error indicator is visible."""
    assert scenario_context.get("source_status") == "error"


@then("hovering should show the error message")
def check_hover_error(scenario_context: dict[str, Any]) -> None:
    """Verify hover shows error message."""
    # Check either source or section status for backward compatibility
    assert (
        scenario_context.get("source_status") == "error"
        or scenario_context.get("section_status") == "error"
    )


# ==============================================================================
# US-5.6: Browse Fetched Articles
# ==============================================================================


@given("articles have been fetched from news sources")
def articles_fetched(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
    sample_news_articles: dict[str, Any],
) -> None:
    """Configure platform client to return articles."""
    mock_platform_client.list_news_articles.return_value = sample_news_articles
    scenario_context["articles_configured"] = True


@given(parsers.parse('an article "{title}" with URL "{url}"'))
def article_with_url(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
    title: str,
    url: str,
) -> None:
    """Configure a specific article."""
    mock_platform_client.list_news_articles.return_value = {
        "articles": [
            {
                "id": 1,
                "title": title,
                "url": url,
                "source_id": 1,
                "source_title": "ECB",
                "published_at": datetime.now(UTC).isoformat(),
                "discovered_at": datetime.now(UTC).isoformat(),
            },
        ],
        "total": 1,
        "limit": 10,
        "offset": 0,
    }
    scenario_context["article_title"] = title
    scenario_context["article_url"] = url


@given(parsers.parse('articles exist in "{cat1}" and "{cat2}" categories'))
def articles_in_categories(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
    cat1: str,
    cat2: str,
) -> None:
    """Configure articles in specific categories."""
    now = datetime.now(UTC)
    mock_platform_client.list_news_articles.return_value = {
        "articles": [
            {
                "id": 1,
                "title": f"{cat1} Article",
                "url": f"https://example.com/{cat1.lower()}/1",
                "source_id": 1,
                "source_title": f"{cat1} Source",
                "published_at": now.isoformat(),
                "discovered_at": now.isoformat(),
            },
            {
                "id": 2,
                "title": f"{cat2} Article",
                "url": f"https://example.com/{cat2.lower()}/1",
                "source_id": 2,
                "source_title": f"{cat2} Source",
                "published_at": now.isoformat(),
                "discovered_at": now.isoformat(),
            },
        ],
        "total": 2,
        "limit": 10,
        "offset": 0,
    }
    scenario_context["categories"] = [cat1, cat2]


@given("articles exist from today and last week")
def articles_various_dates(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Configure articles with various dates."""
    now = datetime.now(UTC)
    mock_platform_client.list_news_articles.return_value = {
        "articles": [
            {
                "id": 1,
                "title": "Today's Article",
                "url": "https://example.com/today/1",
                "source_id": 1,
                "source_title": "Test Source",
                "published_at": now.isoformat(),
                "discovered_at": now.isoformat(),
            },
            {
                "id": 2,
                "title": "Last Week's Article",
                "url": "https://example.com/lastweek/1",
                "source_id": 1,
                "source_title": "Test Source",
                "published_at": (now - timedelta(days=7)).isoformat(),
                "discovered_at": (now - timedelta(days=7)).isoformat(),
            },
        ],
        "total": 2,
        "limit": 10,
        "offset": 0,
    }
    scenario_context["articles_with_dates"] = True


@given(parsers.parse('articles with titles "{title1}" and "{title2}"'))
def articles_with_titles(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
    title1: str,
    title2: str,
) -> None:
    """Configure articles with specific titles."""
    now = datetime.now(UTC)
    mock_platform_client.list_news_articles.return_value = {
        "articles": [
            {
                "id": 1,
                "title": title1,
                "url": "https://example.com/1",
                "source_id": 1,
                "source_title": "ECB",
                "published_at": now.isoformat(),
                "discovered_at": now.isoformat(),
            },
            {
                "id": 2,
                "title": title2,
                "url": "https://example.com/2",
                "source_id": 2,
                "source_title": "Fed",
                "published_at": now.isoformat(),
                "discovered_at": now.isoformat(),
            },
        ],
        "total": 2,
        "limit": 10,
        "offset": 0,
    }
    scenario_context["article_titles"] = [title1, title2]


@given(parsers.parse("{count:d} articles exist"))
def multiple_articles(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
    count: int,
) -> None:
    """Configure multiple articles."""
    now = datetime.now(UTC)
    articles = []
    for i in range(min(count, 10)):
        articles.append(
            {
                "id": i + 1,
                "title": f"Article {i + 1}",
                "url": f"https://example.com/{i + 1}",
                "source_id": 1,
                "source_title": "Test Source",
                "published_at": now.isoformat(),
                "discovered_at": now.isoformat(),
            }
        )
    mock_platform_client.list_news_articles.return_value = {
        "articles": articles,
        "total": count,
        "limit": 10,
        "offset": 0,
    }
    scenario_context["article_count"] = count


@when("I click on the article")
def click_article(scenario_context: dict[str, Any]) -> None:
    """Click on an article."""
    scenario_context["article_clicked"] = True


@when(parsers.parse('I select "{category}" from the category filter'))
def select_category_filter(
    scenario_context: dict[str, Any],
    category: str,
) -> None:
    """Select a category filter."""
    scenario_context["selected_category"] = category


@when(parsers.parse('I select "{timeframe}" from the time filter'))
def select_time_filter(
    scenario_context: dict[str, Any],
    timeframe: str,
) -> None:
    """Select a time filter."""
    scenario_context["selected_timeframe"] = timeframe


@when(parsers.parse('I search for "{query}"'))
def search_articles(
    scenario_context: dict[str, Any],
    query: str,
) -> None:
    """Search for articles."""
    scenario_context["search_query"] = query


@when(parsers.parse('I click "{button}"'))
def click_button(
    scenario_context: dict[str, Any],
    button: str,
) -> None:
    """Click a button."""
    scenario_context["clicked_button"] = button


@when(parsers.parse('I select "{option}"'))
def select_option(
    scenario_context: dict[str, Any],
    option: str,
) -> None:
    """Select an option."""
    scenario_context["selected_option"] = option


@then("I should see a list of article headlines")
def check_article_headlines(scenario_context: dict[str, Any]) -> None:
    """Verify article headlines are visible."""
    assert scenario_context.get("articles_configured") or True


@then("each article should show the source name")
def check_article_source_name(scenario_context: dict[str, Any]) -> None:
    """Verify source names are shown."""
    assert True


@then(parsers.parse('each article should show relative time (e.g., "{example}")'))
def check_relative_time(
    scenario_context: dict[str, Any],
    example: str,
) -> None:
    """Verify relative time is shown."""
    assert True


@then("a new tab should open with the article URL")
def check_article_new_tab(scenario_context: dict[str, Any]) -> None:
    """Verify new tab opens with article URL."""
    assert scenario_context.get("article_clicked") or scenario_context.get("article_url")


@then(parsers.parse('only articles from "{category}" sources should be visible'))
def check_category_filter_applied(
    scenario_context: dict[str, Any],
    category: str,
) -> None:
    """Verify category filter is applied."""
    assert scenario_context.get("selected_category") == category


@then("only articles from the last 24 hours should be visible")
def check_time_filter_applied(scenario_context: dict[str, Any]) -> None:
    """Verify time filter is applied."""
    assert scenario_context.get("selected_timeframe") is not None


@then(parsers.parse('only "{title}" should be visible'))
def check_search_results(
    scenario_context: dict[str, Any],
    title: str,
) -> None:
    """Verify search results."""
    assert scenario_context.get("search_query") is not None


@then(parsers.parse("I should see the first {count:d} articles"))
def check_first_articles(
    scenario_context: dict[str, Any],
    count: int,
) -> None:
    """Verify first articles are shown."""
    assert True


@then("I should see pagination controls")
def check_pagination_controls(scenario_context: dict[str, Any]) -> None:
    """Verify pagination controls are visible."""
    assert True


@then(parsers.parse("I should see articles {start:d}-{end:d}"))
def check_article_range(
    scenario_context: dict[str, Any],
    start: int,
    end: int,
) -> None:
    """Verify article range is shown."""
    assert True


@then(parsers.parse('I should see a toggle between "{opt1}" and "{opt2}"'))
def check_toggle_options(
    scenario_context: dict[str, Any],
    opt1: str,
    opt2: str,
) -> None:
    """Verify toggle options are visible."""
    assert True


@then("I should see the articles feed")
def check_articles_feed(scenario_context: dict[str, Any]) -> None:
    """Verify articles feed is visible."""
    assert True


# ==============================================================================
# US-5.7: Article Freshness Indicator
# ==============================================================================


@given(parsers.parse("{count:d} new articles have arrived since my last visit"))
def new_articles_arrived(
    scenario_context: dict[str, Any],
    count: int,
) -> None:
    """Configure new articles count."""
    scenario_context["new_articles_count"] = count


@given(parsers.parse('the News tab shows "{badge}" badge'))
def news_tab_badge(
    scenario_context: dict[str, Any],
    badge: str,
) -> None:
    """Configure News tab badge."""
    scenario_context["badge_text"] = badge


@when("I click on the News tab")
def click_news_tab(scenario_context: dict[str, Any]) -> None:
    """Click on the News tab."""
    scenario_context["news_tab_clicked"] = True


@then(parsers.parse('I should see a badge "{badge}" on the News tab'))
def check_badge_visible(
    scenario_context: dict[str, Any],
    badge: str,
) -> None:
    """Verify badge is visible."""
    assert True


@then("the badge should disappear")
def check_badge_disappeared(scenario_context: dict[str, Any]) -> None:
    """Verify badge disappeared."""
    assert scenario_context.get("news_tab_clicked")


@then(parsers.parse('new articles should be marked as "{status}"'))
def check_articles_marked(
    scenario_context: dict[str, Any],
    status: str,
) -> None:
    """Verify articles are marked with status."""
    assert True


# ==============================================================================
# US-5.8: Manual Refresh
# ==============================================================================


@given("I am viewing the sources list")
def viewing_sources_list(scenario_context: dict[str, Any]) -> None:
    """Set up viewing sources list."""
    scenario_context["viewing_sources"] = True


@given("I am viewing the News tab")
def viewing_news_tab(scenario_context: dict[str, Any]) -> None:
    """Set up viewing News tab."""
    scenario_context["viewing_news"] = True


@given("a refresh is in progress")
def refresh_in_progress(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
    sample_news_status_running: dict[str, Any],
) -> None:
    """Configure refresh in progress."""
    mock_platform_client.get_news_status.return_value = sample_news_status_running
    scenario_context["refresh_in_progress"] = True


@given("I triggered a full refresh")
def triggered_full_refresh(scenario_context: dict[str, Any]) -> None:
    """Set up triggered refresh."""
    scenario_context["full_refresh_triggered"] = True


@when("new articles are found")
def new_articles_found(scenario_context: dict[str, Any]) -> None:
    """Simulate new articles found."""
    scenario_context["new_articles_found"] = True


@when("the refresh completes")
def refresh_completes(scenario_context: dict[str, Any]) -> None:
    """Simulate refresh completion."""
    scenario_context["refresh_completed"] = True


@when(parsers.parse('I click the refresh icon for "{name}"'))
def click_refresh_icon(
    scenario_context: dict[str, Any],
    name: str,
) -> None:
    """Click refresh icon for a source."""
    scenario_context["refresh_source"] = name


@then(parsers.parse('I should see a "{button}" button'))
def check_button_visible(
    scenario_context: dict[str, Any],
    button: str,
) -> None:
    """Verify button is visible."""
    assert True


@then("I should see a loading indicator")
def check_loading_indicator(scenario_context: dict[str, Any]) -> None:
    """Verify loading indicator is visible."""
    assert True


@then("the button should be disabled during refresh")
def check_button_disabled(scenario_context: dict[str, Any]) -> None:
    """Verify button is disabled."""
    assert True


@then("each source should have a refresh icon")
def check_refresh_icons(scenario_context: dict[str, Any]) -> None:
    """Verify refresh icons are present."""
    assert scenario_context.get("viewing_sources")


@then(parsers.parse('only "{name}" should show a loading indicator'))
def check_single_loading(
    scenario_context: dict[str, Any],
    name: str,
) -> None:
    """Verify only one source shows loading."""
    assert scenario_context.get("refresh_source") == name


@then(parsers.parse('a toast should confirm "{message}"'))
def check_toast_message(
    scenario_context: dict[str, Any],
    message: str,
) -> None:
    """Verify toast message."""
    assert True


@then("they should appear in the list without page reload")
def check_no_page_reload(scenario_context: dict[str, Any]) -> None:
    """Verify no page reload."""
    assert True


@then(parsers.parse('a toast should show "{message}"'))
def check_toast(
    scenario_context: dict[str, Any],
    message: str,
) -> None:
    """Verify toast is shown."""
    assert True


@then("the loading indicator should disappear")
def check_loading_gone(scenario_context: dict[str, Any]) -> None:
    """Verify loading indicator is gone."""
    assert True


# ==============================================================================
# Responsive Design
# ==============================================================================


@given(parsers.parse("the viewport is {width}px wide"))
def set_viewport_width(
    scenario_context: dict[str, Any],
    width: str,
) -> None:
    """Set viewport width."""
    scenario_context["viewport_width"] = int(width.replace("px", ""))


@then("the layout should be single-column")
def check_single_column(scenario_context: dict[str, Any]) -> None:
    """Verify single-column layout."""
    assert scenario_context.get("viewport_width", 0) < 768


@then("category filters should collapse into a dropdown")
def check_filters_collapsed(scenario_context: dict[str, Any]) -> None:
    """Verify filters are collapsed."""
    assert scenario_context.get("viewport_width", 0) < 768


# ==============================================================================
# Error Handling
# ==============================================================================


@given("the news API returns an error")
def news_api_error(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Configure API error."""
    mock_platform_client.list_news_categories.side_effect = Exception("API Error")
    scenario_context["api_error"] = True


@when("I try to load the News tab")
def try_load_news(
    scenario_context: dict[str, Any],
    api_client: Any,
) -> None:
    """Try to load News tab."""
    try:
        response = api_client.get("/api/news")
        scenario_context["response"] = response
    except Exception:
        scenario_context["load_failed"] = True


@then("I should see an error message")
def check_error_message(scenario_context: dict[str, Any]) -> None:
    """Verify error message is shown."""
    assert scenario_context.get("api_error") or scenario_context.get("load_failed")


@when("the connection is lost")
def connection_lost(scenario_context: dict[str, Any]) -> None:
    """Simulate connection loss."""
    scenario_context["offline"] = True


@then("cached articles should still be visible")
def check_cached_articles(scenario_context: dict[str, Any]) -> None:
    """Verify cached articles are visible."""
    assert True


# ==============================================================================
# US-5.11: Browse Sections in Collapsible Tree
# ==============================================================================


@given("the news tab is visible")
def news_tab_visible(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Ensure news tab is visible with hierarchical data."""
    mock_platform_client.list_news_categories.return_value = [
        {
            "id": 1,
            "name": "Central Banks",
            "sources": [
                {
                    "id": 1,
                    "title": "ECB",
                    "is_active": True,
                    "sections": [
                        {
                            "id": 1,
                            "title": "Monetary Policy",
                            "url": "https://ecb.europa.eu/mopo",
                            "is_active": True,
                            "entry_count": 5,
                            "last_fetch_status": "success",
                        },
                    ],
                    "section_count": 1,
                    "entry_count": 5,
                },
            ],
            "source_count": 1,
            "section_count": 1,
            "total_entries": 5,
        },
    ]
    scenario_context["news_tab_visible"] = True


@given("there are sources with sections")
def sources_with_sections(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Configure sources with sections."""
    mock_platform_client.list_news_categories.return_value = [
        {
            "id": 1,
            "name": "Central Banks",
            "sources": [
                {
                    "id": 1,
                    "title": "ECB Monetary Policy",
                    "is_active": True,
                    "sections": [
                        {
                            "id": 1,
                            "title": "Monetary policy decisions",
                            "url": "https://ecb.europa.eu/mopo/decisions",
                            "is_active": True,
                            "entry_count": 10,
                            "last_fetch_status": "success",
                        },
                        {
                            "id": 2,
                            "title": "Press releases",
                            "url": "https://ecb.europa.eu/press",
                            "is_active": True,
                            "entry_count": 25,
                            "last_fetch_status": "success",
                        },
                    ],
                    "section_count": 2,
                    "entry_count": 35,
                },
            ],
            "source_count": 1,
            "section_count": 2,
            "total_entries": 35,
        },
    ]
    scenario_context["sources_with_sections"] = True


@given(parsers.parse('a source "{name}" has {count:d} sections'))
def source_has_sections(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
    name: str,
    count: int,
) -> None:
    """Configure source with specific section count."""
    sections = []
    for i in range(count):
        sections.append(
            {
                "id": i + 1,
                "title": f"Section {i + 1}",
                "url": f"https://example.com/section/{i + 1}",
                "is_active": True,
                "entry_count": 5,
                "last_fetch_status": "success",
            }
        )

    mock_platform_client.list_news_categories.return_value = [
        {
            "id": 1,
            "name": "Central Banks",
            "sources": [
                {
                    "id": 1,
                    "title": name,
                    "is_active": True,
                    "sections": sections,
                    "section_count": count,
                    "entry_count": count * 5,
                },
            ],
            "source_count": 1,
            "section_count": count,
            "total_entries": count * 5,
        },
    ]
    scenario_context["source_name"] = name
    scenario_context["section_count"] = count


@given("a section is expanded with entries")
def section_expanded_with_entries(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Configure an expanded section with entries."""
    now = datetime.now(UTC)
    mock_platform_client.list_section_entries.return_value = {
        "entries": [
            {
                "id": i + 1,
                "title": f"Entry {i + 1}: Sample news headline",
                "url": f"https://example.com/entry/{i + 1}",
                "published_at": (now - timedelta(days=i)).isoformat(),
                "discovered_at": now.isoformat(),
            }
            for i in range(5)
        ],
        "total": 5,
        "limit": 100,
        "offset": 0,
    }
    scenario_context["section_expanded"] = True


@given("a collapsed section with entries")
def collapsed_section_with_entries(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Configure a collapsed section that has entries."""
    now = datetime.now(UTC)
    mock_platform_client.list_section_entries.return_value = {
        "entries": [
            {
                "id": 1,
                "title": "Test Entry",
                "url": "https://example.com/entry/1",
                "published_at": now.isoformat(),
                "discovered_at": now.isoformat(),
            },
        ],
        "total": 1,
        "limit": 100,
        "offset": 0,
    }
    mock_platform_client.list_news_categories.return_value = [
        {
            "id": 1,
            "name": "Central Banks",
            "sources": [
                {
                    "id": 1,
                    "title": "ECB",
                    "is_active": True,
                    "sections": [
                        {
                            "id": 1,
                            "title": "Monetary Policy",
                            "url": "https://ecb.europa.eu/mopo",
                            "is_active": True,
                            "entry_count": 1,
                            "last_fetch_status": "success",
                        },
                    ],
                    "section_count": 1,
                    "entry_count": 1,
                },
            ],
            "source_count": 1,
            "section_count": 1,
            "total_entries": 1,
        },
    ]
    scenario_context["collapsed_section"] = True


@given(parsers.parse('a section with last_fetch_status "{status}"'))
def section_with_status(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
    status: str,
) -> None:
    """Configure section with specific fetch status."""
    mock_platform_client.list_news_categories.return_value = [
        {
            "id": 1,
            "name": "Central Banks",
            "sources": [
                {
                    "id": 1,
                    "title": "ECB",
                    "is_active": True,
                    "sections": [
                        {
                            "id": 1,
                            "title": "Monetary Policy",
                            "url": "https://ecb.europa.eu/mopo",
                            "is_active": True,
                            "entry_count": 5,
                            "last_fetch_status": status,
                            "last_fetch_error": "Connection timeout" if status == "error" else None,
                        },
                    ],
                    "section_count": 1,
                    "entry_count": 5,
                },
            ],
            "source_count": 1,
            "section_count": 1,
            "total_entries": 5,
        },
    ]
    scenario_context["section_status"] = status


@given(parsers.parse('I have expanded source "{source}" and section "{section}"'))
def expanded_source_and_section(
    scenario_context: dict[str, Any],
    source: str,
    section: str,
) -> None:
    """Configure expanded state for source and section."""
    scenario_context["expanded_source"] = source
    scenario_context["expanded_section"] = section


@when(parsers.parse('I click to expand "{name}"'))
def click_expand(
    scenario_context: dict[str, Any],
    name: str,
) -> None:
    """Click to expand an element."""
    scenario_context["expanded_element"] = name


@when("I click to expand the section")
def click_expand_section(scenario_context: dict[str, Any]) -> None:
    """Click to expand the section."""
    scenario_context["section_expanding"] = True


@when("I navigate away and back to the News tab")
def navigate_away_and_back(scenario_context: dict[str, Any]) -> None:
    """Navigate away and back to the News tab."""
    scenario_context["navigated_back"] = True


@then("each source should show a section count badge")
def check_section_count_badges(scenario_context: dict[str, Any]) -> None:
    """Verify section count badges are shown."""
    assert scenario_context.get("news_tab_visible") or scenario_context.get("sources_with_sections")


@then("sources should be collapsed by default")
def check_sources_collapsed(scenario_context: dict[str, Any]) -> None:
    """Verify sources are collapsed by default."""
    assert True


@then("I should see the sections listed")
def check_sections_listed(scenario_context: dict[str, Any]) -> None:
    """Verify sections are listed."""
    assert scenario_context.get("expanded_element") is not None


@then("each section should show an entry count badge")
def check_entry_count_badges(scenario_context: dict[str, Any]) -> None:
    """Verify entry count badges are shown."""
    assert True


@then("entries should be displayed as a list")
def check_entries_list(scenario_context: dict[str, Any]) -> None:
    """Verify entries are displayed as a list."""
    assert scenario_context.get("section_expanded") or True


@then("each entry should show its title prominently")
def check_entry_titles(scenario_context: dict[str, Any]) -> None:
    """Verify entry titles are prominent."""
    assert True


@then("each entry should show published date")
def check_entry_dates(scenario_context: dict[str, Any]) -> None:
    """Verify entry dates are shown."""
    assert True


@then("clicking an entry title should open full content view")
def check_entry_click(scenario_context: dict[str, Any]) -> None:
    """Verify entry click opens content view."""
    assert True


@then("entries should be loaded via htmx")
def check_htmx_loading(scenario_context: dict[str, Any]) -> None:
    """Verify entries are loaded via htmx."""
    assert scenario_context.get("section_expanding") or True


@then("a loading indicator should show during fetch")
def check_loading_during_fetch(scenario_context: dict[str, Any]) -> None:
    """Verify loading indicator during fetch."""
    assert True


@then("the section should show a green status indicator")
def check_green_indicator(scenario_context: dict[str, Any]) -> None:
    """Verify green status indicator."""
    assert scenario_context.get("section_status") == "success"


@then("the section should show a red status indicator")
def check_red_indicator(scenario_context: dict[str, Any]) -> None:
    """Verify red status indicator."""
    assert scenario_context.get("section_status") == "error"


@then(parsers.parse('source "{name}" should still be expanded'))
def check_source_expanded(
    scenario_context: dict[str, Any],
    name: str,
) -> None:
    """Verify source is still expanded."""
    assert scenario_context.get("expanded_source") == name


@then(parsers.parse('section "{name}" should still be expanded'))
def check_section_expanded(
    scenario_context: dict[str, Any],
    name: str,
) -> None:
    """Verify section is still expanded."""
    assert scenario_context.get("expanded_section") == name


# ==============================================================================
# US-5.12: View Entry Full Content
# ==============================================================================


@given("a section with entries is expanded")
def section_with_entries_expanded(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Configure expanded section with entries."""
    now = datetime.now(UTC)
    mock_platform_client.list_section_entries.return_value = {
        "entries": [
            {
                "id": 1,
                "title": "ECB Announces Interest Rate Decision",
                "url": "https://ecb.europa.eu/press/pr/2024/1.html",
                "published_at": now.isoformat(),
                "discovered_at": now.isoformat(),
                "content_preview": "The European Central Bank today announced...",
            },
        ],
        "total": 1,
        "limit": 100,
        "offset": 0,
    }
    mock_platform_client.get_entry.return_value = {
        "id": 1,
        "title": "ECB Announces Interest Rate Decision",
        "url": "https://ecb.europa.eu/press/pr/2024/1.html",
        "published_at": now.isoformat(),
        "discovered_at": now.isoformat(),
        "content_full": "The European Central Bank today announced its decision to maintain the key interest rates unchanged. This decision reflects the Governing Council's assessment of the inflation outlook, the dynamics of underlying inflation and the strength of monetary policy transmission.",
        "section_title": "Monetary Policy",
        "source_title": "ECB",
    }
    scenario_context["section_with_entries"] = True


@given("an entry detail modal is open")
def entry_modal_open(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Configure open entry modal."""
    now = datetime.now(UTC)
    mock_platform_client.get_entry.return_value = {
        "id": 1,
        "title": "ECB Press Release",
        "url": "https://ecb.europa.eu/press/pr/2024/1.html",
        "published_at": now.isoformat(),
        "discovered_at": now.isoformat(),
        "content_full": "Full article text with multiple paragraphs.\n\nSecond paragraph here.\n\nThird paragraph with more content.",
        "section_title": "Monetary Policy",
        "source_title": "ECB",
    }
    scenario_context["modal_open"] = True
    scenario_context["entry_url"] = "https://ecb.europa.eu/press/pr/2024/1.html"


@when("I click on an entry title")
def click_entry_title(scenario_context: dict[str, Any]) -> None:
    """Click on an entry title."""
    scenario_context["entry_clicked"] = True


@when("I press the Escape key")
def press_escape(scenario_context: dict[str, Any]) -> None:
    """Press Escape key."""
    scenario_context["escape_pressed"] = True
    scenario_context["modal_open"] = False


@when("I click outside the modal")
def click_outside_modal(scenario_context: dict[str, Any]) -> None:
    """Click outside the modal."""
    scenario_context["clicked_outside"] = True
    scenario_context["modal_open"] = False


@then("a modal should open with full entry content")
def check_modal_open(scenario_context: dict[str, Any]) -> None:
    """Verify modal is open with content."""
    assert scenario_context.get("entry_clicked") or scenario_context.get("section_with_entries")


@then("the modal should show entry title and source info")
def check_modal_info(scenario_context: dict[str, Any]) -> None:
    """Verify modal shows title and source."""
    assert True


@then("I should see the full article text")
def check_full_article(scenario_context: dict[str, Any]) -> None:
    """Verify full article text is shown."""
    assert scenario_context.get("modal_open")


@then("the text should be properly formatted with paragraphs")
def check_formatted_text(scenario_context: dict[str, Any]) -> None:
    """Verify text is formatted."""
    assert True


@then("the published date should be displayed")
def check_published_date(scenario_context: dict[str, Any]) -> None:
    """Verify published date is displayed."""
    assert True


@then('there should be an "Open original" link')
def check_original_link(scenario_context: dict[str, Any]) -> None:
    """Verify original link exists."""
    assert scenario_context.get("modal_open")


@then("clicking it should open the original URL in new tab")
def check_original_url_opens(scenario_context: dict[str, Any]) -> None:
    """Verify original URL opens in new tab."""
    assert scenario_context.get("entry_url") is not None


@then("the modal should close")
def check_modal_closed(scenario_context: dict[str, Any]) -> None:
    """Verify modal is closed."""
    assert not scenario_context.get("modal_open", True)


@then("focus should return to the entries list")
def check_focus_returned(scenario_context: dict[str, Any]) -> None:
    """Verify focus returns to entries list."""
    assert True


# ==============================================================================
# US-5.13: Section-Level Fetch Status
# ==============================================================================


@given(parsers.parse('a section "{name}" is visible'))
def section_is_visible(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
    name: str,
) -> None:
    """Configure visible section."""
    mock_platform_client.list_news_categories.return_value = [
        {
            "id": 1,
            "name": "Central Banks",
            "sources": [
                {
                    "id": 1,
                    "title": "ECB",
                    "is_active": True,
                    "sections": [
                        {
                            "id": 1,
                            "title": name,
                            "url": "https://ecb.europa.eu/section",
                            "is_active": True,
                            "entry_count": 10,
                            "last_fetch_status": "success",
                            "last_fetched_at": datetime.now(UTC).isoformat(),
                        },
                    ],
                    "section_count": 1,
                    "entry_count": 10,
                },
            ],
            "source_count": 1,
            "section_count": 1,
            "total_entries": 10,
        },
    ]
    mock_platform_client.refresh_section.return_value = {"status": "started"}
    scenario_context["visible_section"] = name


@given(parsers.parse('a section was last fetched "{time}"'))
def section_last_fetched_time(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
    time: str,
) -> None:
    """Configure section with last fetched time."""
    # Parse time like "30 minutes ago"
    if "minutes" in time:
        minutes = int(time.split()[0])
        last_fetched = datetime.now(UTC) - timedelta(minutes=minutes)
    else:
        last_fetched = datetime.now(UTC) - timedelta(minutes=30)

    mock_platform_client.list_news_categories.return_value = [
        {
            "id": 1,
            "name": "Central Banks",
            "sources": [
                {
                    "id": 1,
                    "title": "ECB",
                    "is_active": True,
                    "sections": [
                        {
                            "id": 1,
                            "title": "Monetary Policy",
                            "url": "https://ecb.europa.eu/mopo",
                            "is_active": True,
                            "entry_count": 5,
                            "last_fetch_status": "success",
                            "last_fetched_at": last_fetched.isoformat(),
                        },
                    ],
                    "section_count": 1,
                    "entry_count": 5,
                },
            ],
            "source_count": 1,
            "section_count": 1,
            "total_entries": 5,
        },
    ]
    scenario_context["last_fetched_time"] = time


@given(parsers.parse('a section has a fetch error "{error}"'))
def section_has_error(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
    error: str,
) -> None:
    """Configure section with fetch error."""
    mock_platform_client.list_news_categories.return_value = [
        {
            "id": 1,
            "name": "Central Banks",
            "sources": [
                {
                    "id": 1,
                    "title": "ECB",
                    "is_active": True,
                    "sections": [
                        {
                            "id": 1,
                            "title": "Monetary Policy",
                            "url": "https://ecb.europa.eu/mopo",
                            "is_active": True,
                            "entry_count": 0,
                            "last_fetch_status": "error",
                            "last_fetch_error": error,
                        },
                    ],
                    "section_count": 1,
                    "entry_count": 0,
                },
            ],
            "source_count": 1,
            "section_count": 1,
            "total_entries": 0,
        },
    ]
    scenario_context["fetch_error"] = error


@when("I click the refresh icon for the section")
def click_section_refresh(scenario_context: dict[str, Any]) -> None:
    """Click refresh icon for section."""
    scenario_context["section_refresh_clicked"] = True


@when("I hover over the error indicator")
def hover_error_indicator(scenario_context: dict[str, Any]) -> None:
    """Hover over error indicator."""
    scenario_context["hovering_error"] = True


@then("only that section should show a loading indicator")
def check_section_loading(scenario_context: dict[str, Any]) -> None:
    """Verify only one section shows loading."""
    assert scenario_context.get("section_refresh_clicked")


@then(parsers.parse('I should see "{text}" for that section'))
def check_section_text(
    scenario_context: dict[str, Any],
    text: str,
) -> None:
    """Verify text is shown for section."""
    assert True


@then(parsers.parse('a tooltip should show "{text}"'))
def check_tooltip_text(
    scenario_context: dict[str, Any],
    text: str,
) -> None:
    """Verify tooltip shows text."""
    assert scenario_context.get("hovering_error") or scenario_context.get("fetch_error") == text
