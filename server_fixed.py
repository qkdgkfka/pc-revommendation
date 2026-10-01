#!/usr/bin/env python3

"""Compatibility entry point; domain implementation lives in pcbuilder."""

from pcbuilder.database import (
    _best_match_key,
    _ensure_db_connection,
    db_lookup_price,
    db_lookup_price_info,
    ensure_db_cache_loaded,
    get_or_fetch_danawa_price,
    init_db_schema,
    insert_price,
    load_config,
    load_db_cache,
    market_lookup_name,
    market_product_url,
    part_image_endpoint,
    price_is_fresh,
    store_danawa_price,
    table_columns,
    upsert_component,
    verified_price_info,
)

from pcbuilder.fps import (
    adjust_benchmark_quality,
    attach_graphics_modes,
    average_benchmark_rows,
    benchmark_row_for_gpu,
    cpu_fps_factor,
    db_lookup_benchmarks,
    estimate_fps_bundle,
    estimate_fps_from_catalog,
    estimate_fps_from_db,
    find_catalog_part,
    fps_estimate_response,
    game_frame_cap,
    game_genre_for_id,
    game_key_variants,
    gpu_base_perf,
    hierarchy_fps,
    normalized_game_key,
    part_price,
    quality_scale,
    ram_fps_factor,
    resolve_fps_part,
    target_fps_for_game,
)

from pcbuilder.http import (
    Handler,
    catalog_response,
    main,
    meta_content_from_soup,
    page_preview_meta,
    parse_args,
    placeholder_svg,
    resolve_part_image_url,
    safe_external_url,
    saved_part_image_urls,
    send_json,
    send_page_preview,
    send_part_image,
)

from pcbuilder.pricing import (
    apply_price_info_to_part,
    budget_allocations,
    collect_display_parts,
    component_performance_index,
    fps_capacity_label,
    game_profile,
    is_recommendable_gpu,
    low1_ratio_for_genres,
    price_lookup_response,
    product_search_response,
    recompute_plan_total,
    refresh_recommendation_prices,
    resolve_recommendation_price_cache,
    resolve_verified_gpu_market_prices,
    summarize_part,
    value_label,
    value_metrics,
)

from pcbuilder.recommendation import (
    CandidateEvaluationCache,
    RecommendationRequest,
    build_power_score,
    build_tier_candidates,
    cached_part_price,
    complete_recommendation_tiers,
    estimate_work_scores,
    filter_compatible_mb,
    filter_compatible_ram,
    is_desktop_cpu,
    is_desktop_mb,
    make_plan_from_raw_parts,
    mb_candidates_for,
    normalize_work_profile,
    part_cache_key,
    part_tags,
    plan_ordering_metrics,
    price_sum_for_parts,
    psu_candidates_for,
    rank_parts_for_tier,
    recommend,
    recommended_psu_watt,
    score_cpu,
    score_gpu,
    score_ram,
    score_storage,
    score_work_profile,
    select_ordered_tier_plans,
    storage_candidates_for,
    target_power_score,
    tier_budget_for_user,
    tier_component_pools,
    tier_rank,
    tier_upgrade_quality,
    verified_recommendation_inventory,
    work_component_norms,
    work_suitability,
)

from pcbuilder.retail import (
    _market_fetch_html,
    _market_source_page,
    absolute_image_url,
    catalog_reference_price,
    category_from_danawa_block,
    clamp,
    compuzone_browse_url,
    danawa_browse_candidate_valid,
    danawa_browse_category_matches,
    danawa_browse_tier,
    danawa_browse_url,
    danawa_candidate_valid,
    danawa_category_matches,
    danawa_name_rejected,
    danawa_product_code,
    danawa_query_for_part,
    danawa_search_url,
    danawa_url_category_id,
    danawa_url_category_matches,
    danawa_url_rejected,
    enrich_danawa_browse_product,
    fetch_market_top_product,
    first_anchor_from_block,
    html_attribute,
    image_from_danawa_block,
    market_component_name_valid,
    market_products_response,
    parse_compuzone_browse_products,
    parse_danawa_browse_products,
    parse_danawa_top_product,
    parse_danawa_top_product_regex,
    performance_reference_for_danawa_product,
    price_sane_for_part,
    retail_quote_valid,
    saved_market_page,
)

from pcbuilder.runtime import (
    APP_DIR,
    ARTIFACT_DIR,
    BENCHMARK_LOOKUP_CACHE,
    COMPUZONE_CATEGORY_IDS,
    CONFIG_PATH,
    DANAWA_BROWSE_CACHE_TTL_SECONDS,
    DANAWA_BROWSE_CATEGORY_IDS,
    DANAWA_HEADERS,
    DANAWA_PRICE_MAX_AGE_HOURS,
    DATA_DIR,
    DB_CACHE,
    DB_PATH,
    DISPLAY_PRICE_TYPES,
    GAME_FRAME_CAPS,
    GAME_GENRE_FACTORS,
    GPU_DANAWA_CATEGORY_IDS,
    GPU_MARKET_PRICE_CACHE,
    GPU_MARKET_PRICE_CHECKED_AT,
    HYBRID_CONFIG,
    IMAGE_URL_CACHE,
    MARKET_BROWSE_CACHE,
    MARKET_SEARCH_CACHE,
    MARKET_SEARCH_LOCK,
    MB_DANAWA_CATEGORY_IDS,
    MODEL_LOADED,
    PREVIEW_CACHE,
    RECOMMENDATION_CACHE,
    STATIC_DIR,
    STORAGE_DANAWA_CATEGORY_IDS,
    TIER_RANK,
)

from server_catalogs import (
    BENCHMARK_FPS_BY_GPU,
    CASE_CATALOG,
    CATALOGS,
    COMMON_GPU_MODEL_NUMBERS,
    CPU_CATALOG,
    GAME_FPS_PROFILES,
    GAME_OPTIONS,
    GPU_CATALOG,
    HDD_CATALOG,
    MB_CATALOG,
    PSU_CATALOG,
    RAM_CATALOG,
    SOFTWARE_CATALOG,
    STORAGE_CATALOG,
    WORK_ALIASES,
    WORK_PROFILES,
)

from pcbuilder.retail import (
    BeautifulSoup,
)

from product_metadata import (
    DANAWA_BROWSE_DEFAULT_QUERIES,
    GPU_MAKER_ALIASES,
    GPU_MAKER_LABELS,
    canonical_name,
    capacity_mb_from_text,
    clean_visible_text,
    compatible_gpu_price_name,
    compatible_price_name,
    gpu_exact_model_key,
    gpu_maker_label,
    gpu_maker_normalize,
    gpu_model_number_from_key,
    gpu_model_number_mentions,
    gpu_search_metadata,
    gpu_series_key,
    image_name_tokens,
    infer_brand,
    infer_cpu_metadata,
    infer_gpu_vram,
    infer_hdd_rpm,
    infer_mb_metadata,
    infer_psu_watt,
    model_tokens,
    normalize_browse_part_type,
    normalize_gpu_maker_prefs,
    normalize_product_url,
    normalize_text,
    parse_price_value,
    parse_ram_metadata,
    query_model_name,
    safe_float,
    safe_int,
    strip_html,
    variant_tokens,
)

from product_filters import (
    FIELDS as PRODUCT_FILTER_FIELDS,
    clean_filters,
    enrich as enrich_product,
    matches_specs,
    normalize_specs,
    facets as product_facets,
)

from market_search import (
    ProductPager,
    RetailQueryStream,
)

from recommendation_policy import (
    build_preference,
    cpu_allowed,
    cpu_preference,
    cpu_vendor,
    gpu_preference,
    gpu_product_band,
    objective_score,
    storage_preference,
)

from retailer_parsing import (
    danawa_candidate_blocks,
    price_from_danawa_block,
)

from game_benchmarks import (
    estimate_from_measurements,
    load_measurements,
)

from product_images import (
    fetch_product_image,
    fetch_product_page_image,
    image_source_priority,
    product_page_key,
    retailer_image_url,
)

from product_import import (
    fetch_product_page,
    imported_products,
    supported_product_url,
)

from graphics_estimates import (
    graphics_scenarios,
)

from component_compatibility import (
    platform_compatibility,
)

from market_catalog import (
    remember_products,
    saved_products,
)

from pcbuilder.utils import (
    genres_normalize,
    guess_mime,
    refresh_value,
    resolution_key,
    stable_seed,
    vendor_normalize,
)

if __name__ == '__main__':
    main()
