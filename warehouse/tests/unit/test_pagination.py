from app.core.pagination import PaginationParams, build_pagination_metadata


def test_pagination_params_offset_and_limit():
    p1 = PaginationParams(page=1, page_size=20)
    assert p1.offset == 0
    assert p1.limit == 20

    p2 = PaginationParams(page=3, page_size=50)
    assert p2.offset == 100
    assert p2.limit == 50


def test_build_pagination_metadata():
    params = PaginationParams(page=2, page_size=25)
    meta = build_pagination_metadata(total=105, params=params)

    assert meta.page == 2
    assert meta.page_size == 25
    assert meta.total == 105
    assert meta.total_pages == 5  # 105 // 25 = 4 remainder 5 -> 5 pages


def test_build_pagination_metadata_zero_total():
    params = PaginationParams(page=1, page_size=50)
    meta = build_pagination_metadata(total=0, params=params)

    assert meta.page == 1
    assert meta.total == 0
    assert meta.total_pages == 0


def test_build_pagination_metadata_exact_page():
    params = PaginationParams(page=1, page_size=50)
    meta = build_pagination_metadata(total=100, params=params)

    assert meta.total_pages == 2
