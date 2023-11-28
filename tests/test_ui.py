import pytest
from playwright.sync_api import Page, expect


def test_initial_load(page: Page, screenshot_snapshot, ds_server):
    page.goto(f"{ds_server}/-/datasette-comments/tags/tag1")


def client_login_as(page: Page, actor_id: str):
    page.context.add_cookies(
        [
            {
                "name": "actor",
                "value": actor_id,
                "url": "http://localhost:8123",  # "domain": "", "path": "/"
            }
        ]
    )


@pytest.mark.skip(reason="need to figure out authenticated users")
def test_table_view_manual(page: Page, screenshot_snapshot, ds_server):
    client_login_as(page, "2")

    page.goto(f"{ds_server}/my_data/students")
    table = page.locator("table")
    assert table.locator("tbody tr").count() == 3

    aaa_id_td = page.locator("table tbody tr:nth-child(1) td:nth-child(1)")
    bbb_id_td = page.locator("table tbody tr:nth-child(2) td:nth-child(1)")
    ccc_id_td = page.locator("table tbody tr:nth-child(3) td:nth-child(1)")

    expect(aaa_id_td.locator("button")).to_be_visible()
    expect(bbb_id_td.locator("button")).not_to_be_visible()

    bbb_id_td_rect = bbb_id_td.bounding_box()
    page.mouse.move(bbb_id_td_rect["x"], bbb_id_td_rect["y"])
    expect(bbb_id_td.locator("button")).to_be_visible()

    expect(page.locator("textarea")).to_have_count(0)
    bbb_id_td.click()
    expect(page.locator("textarea")).to_have_count(1)
    page.locator("textarea").fill("A new comment! #lol")
    page.locator(".draft-add-button").click()

    # make sure that new comment show up in the table now!
    page.reload()
    bbb_id_td = page.locator("table tbody tr:nth-child(2) td:nth-child(1)")
    expect(bbb_id_td.locator("button")).to_be_visible()


@pytest.mark.skip(reason="no screenshot tests yet")
def test_table_view_screenshots(page: Page, screenshot_snapshot, ds_server):
    client_login_as("2")

    page.goto(f"{ds_server}/my_data/students")
    table = page.locator("table")
    assert table.screenshot() == screenshot_snapshot(name="table")

    aaa_id_td = page.locator("table tbody tr:nth-child(1) td:nth-child(1)")
    bbb_id_td = page.locator("table tbody tr:nth-child(2) td:nth-child(1)")

    # when a user hovers over a row with no comments, it should show the "comment" icon
    bbb_id_td_rect = bbb_id_td.bounding_box()
    page.mouse.move(bbb_id_td_rect["x"], bbb_id_td_rect["y"])
    assert table.screenshot() == screenshot_snapshot(name="table-hover-no-comment")

    aaa_id_td.click()

    assert page.screenshot() == screenshot_snapshot(name="table-row-comment-click")
