/**
 * RoadCare AI - Kolhapur Municipal Corporation (KMC) Road Distress Dashboard
 * Area-Wise Multi-Zone Perception, ByteTrack Telemetry & Municipal Triage Workflow
 */

(function () {
  'use strict';

  // Kolhapur Administrative Zones & Geographic Centers
  const KOLHAPUR_ZONES = {
    'Central Kolhapur': {
      name: 'Central Kolhapur Zone',
      title: 'Ward Officer - Central Kolhapur',
      areas: 'Shahupuri • Laxmipuri • Rajarampuri',
      center: [16.7040, 74.2380],
      zoom: 14
    },
    'North Kolhapur': {
      name: 'North Kolhapur Zone',
      title: 'Ward Officer - North Kolhapur',
      areas: 'Ujalaiwadi • Kasaba Bawada side',
      center: [16.7250, 74.2480],
      zoom: 14
    },
    'South Kolhapur': {
      name: 'South Kolhapur Zone',
      title: 'Ward Officer - South Kolhapur',
      areas: 'Kalamba • Morewadi side',
      center: [16.6750, 74.2280],
      zoom: 14
    },
    'East Kolhapur': {
      name: 'East Kolhapur Zone',
      title: 'Ward Officer - East Kolhapur',
      areas: 'Uchgaon • Gokul Shirgaon side',
      center: [16.6850, 74.2750],
      zoom: 14
    },
    'West Kolhapur': {
      name: 'West Kolhapur Zone',
      title: 'Ward Officer - West Kolhapur',
      areas: 'Rankala • Phulewadi side',
      center: [16.6920, 74.2050],
      zoom: 14
    },
    'all': {
      name: 'All Kolhapur City',
      title: 'Chief Municipal Engineer',
      areas: 'All 5 Kolhapur Municipal Zones (Citywide)',
      center: [16.7000, 74.2400],
      zoom: 13
    }
  };

  const ZONE_KEYS = [
    'Central Kolhapur',
    'North Kolhapur',
    'South Kolhapur',
    'East Kolhapur',
    'West Kolhapur',
    'all'
  ];

  // Configuration & State
  const CONFIG = {
    API_BASE: (window.location.origin && window.location.origin.startsWith('http')) ? window.location.origin : 'http://localhost:8000',
    DEFAULT_CENTER: [16.7040, 74.2380], // Central Kolhapur
    DEFAULT_ZOOM: 14,
    STORAGE_KEY: 'roadcare_defects_cache_kolhapur_v2',
    THEME_STORAGE_KEY: 'roadcare_theme',
    ZONE_STORAGE_KEY: 'roadcare_kolhapur_zone',
    AUTH_STORAGE_KEY: 'roadcare_kmc_logged_in',
    BASEMAP_STORAGE_KEY: 'roadcare_basemap'
  };

  const state = {
    defects: [],
    filteredDefects: [],
    selectedDefect: null,
    backendOnline: false,
    map: null,
    tileLayer: null,
    markersLayer: null,
    currentBasemap: localStorage.getItem('roadcare_basemap') || 'google-roads',
    currentTheme: localStorage.getItem(CONFIG.THEME_STORAGE_KEY) || 'light',
    currentZone: localStorage.getItem(CONFIG.ZONE_STORAGE_KEY) || 'Central Kolhapur',
    isLoggedIn: true,
    activeFilter: 'all',
    searchQuery: '',
    selectedSeverity: '',
    selectedStatus: '',
    zoneGeoJSON: null,
    zoneLayers: {},
    zoneCenterMarkers: {},
    zoneStatistics: {},
    zonesLayerGroup: null
  };

  // 25 Verified Kolhapur Municipal Road Distress Detections
  const DEFAULT_SAMPLE_DEFECTS = [
    {
      id: "rec-201",
      defect_id: 201,
      class_name: "pothole",
      severity: "High",
      confidence: 0.942,
      timestamp: "2026-09-15 08:14:22",
      latitude: 16.7052,
      longitude: 74.2410,
      bbox_norm: [0.28, 0.55, 0.26, 0.24],
      zone: "Central Kolhapur",
      area: "Shahupuri",
      street: "Station Road, Near Shahupuri Police Chowki",
      status: "reported",
      assigned_contractor: null,
      notes: "Severe crater in front of station approach."
    },
    {
      id: "rec-202",
      defect_id: 202,
      class_name: "alligator_crack",
      severity: "Medium",
      confidence: 0.887,
      timestamp: "2026-09-15 08:25:40",
      latitude: 16.7025,
      longitude: 74.2320,
      bbox_norm: [0.15, 0.48, 0.42, 0.31],
      zone: "Central Kolhapur",
      area: "Laxmipuri",
      street: "Laxmipuri Vegetable Market Main Road",
      status: "inspected",
      assigned_contractor: "Kolhapur Pavement Works",
      notes: "Fatigue mesh cracking across transit corridor. Sub-base moisture detected."
    },
    {
      id: "rec-203",
      defect_id: 203,
      class_name: "pothole",
      severity: "High",
      confidence: 0.961,
      timestamp: "2026-09-15 08:41:05",
      latitude: 16.6970,
      longitude: 74.2435,
      bbox_norm: [0.38, 0.62, 0.31, 0.27],
      zone: "Central Kolhapur",
      area: "Rajarampuri",
      street: "Rajarampuri 2nd Lane Commercial Junction",
      status: "in_progress",
      assigned_contractor: "Apex Infra Kolhapur",
      notes: "Barricades placed. Asphalt hot-mix patching underway."
    },
    {
      id: "rec-204",
      defect_id: 204,
      class_name: "pothole",
      severity: "Low",
      confidence: 0.793,
      timestamp: "2026-09-15 08:55:12",
      latitude: 16.7060,
      longitude: 74.2425,
      bbox_norm: [0.44, 0.70, 0.12, 0.09],
      zone: "Central Kolhapur",
      area: "Shahupuri",
      street: "Shahupuri 3rd Lane, Near Bank of Maharashtra",
      status: "repaired",
      assigned_contractor: "Civic Road Works",
      notes: "Surface level patch completed with thermoplastic sealing."
    },
    {
      id: "rec-205",
      defect_id: 205,
      class_name: "alligator_crack",
      severity: "High",
      confidence: 0.915,
      timestamp: "2026-09-15 09:12:18",
      latitude: 16.6995,
      longitude: 74.2480,
      bbox_norm: [0.12, 0.40, 0.65, 0.45],
      zone: "Central Kolhapur",
      area: "Rajarampuri",
      street: "Rajarampuri Janata Bazar Main Road",
      status: "reported",
      assigned_contractor: null,
      notes: null
    },
    {
      id: "rec-206",
      defect_id: 206,
      class_name: "pothole",
      severity: "High",
      confidence: 0.978,
      timestamp: "2026-09-15 09:25:04",
      latitude: 16.7280,
      longitude: 74.2510,
      bbox_norm: [0.25, 0.52, 0.34, 0.29],
      zone: "North Kolhapur",
      area: "Kasaba Bawada",
      street: "Kasaba Bawada Main Road (Near D.Y. Patil College)",
      status: "reported",
      assigned_contractor: null,
      notes: null
    },
    {
      id: "rec-207",
      defect_id: 207,
      class_name: "alligator_crack",
      severity: "High",
      confidence: 0.932,
      timestamp: "2026-09-15 09:40:15",
      latitude: 16.7320,
      longitude: 74.2480,
      bbox_norm: [0.10, 0.38, 0.70, 0.48],
      zone: "North Kolhapur",
      area: "Kasaba Bawada",
      street: "Panchganga River Bridge North Approach",
      status: "in_progress",
      assigned_contractor: "North Zone PWD Contractor",
      notes: "Severe base shear failure near river approach. Barricades active."
    },
    {
      id: "rec-208",
      defect_id: 208,
      class_name: "alligator_crack",
      severity: "Medium",
      confidence: 0.864,
      timestamp: "2026-09-15 09:58:44",
      latitude: 16.6690,
      longitude: 74.2790,
      bbox_norm: [0.18, 0.44, 0.52, 0.33],
      zone: "North Kolhapur",
      area: "Ujalaiwadi",
      street: "Ujalaiwadi Kolhapur Airport Access Road",
      status: "inspected",
      assigned_contractor: "National Highways Sub-Div",
      notes: "Interconnected crack network on airport transit avenue."
    },
    {
      id: "rec-209",
      defect_id: 209,
      class_name: "pothole",
      severity: "Medium",
      confidence: 0.849,
      timestamp: "2026-09-15 10:14:30",
      latitude: 16.7210,
      longitude: 74.2460,
      bbox_norm: [0.30, 0.58, 0.22, 0.18],
      zone: "North Kolhapur",
      area: "Kasaba Bawada",
      street: "Line Bazar Approach Road",
      status: "reported",
      assigned_contractor: null,
      notes: null
    },
    {
      id: "rec-210",
      defect_id: 210,
      class_name: "pothole",
      severity: "Low",
      confidence: 0.804,
      timestamp: "2026-09-15 10:30:15",
      latitude: 16.7350,
      longitude: 74.2540,
      bbox_norm: [0.35, 0.60, 0.18, 0.15],
      zone: "North Kolhapur",
      area: "Kasaba Bawada",
      street: "Chhatrapati Shahu Sugar Factory Road",
      status: "repaired",
      assigned_contractor: "Bawada Civic Works",
      notes: "Cold mix asphalt leveling completed."
    },
    {
      id: "rec-211",
      defect_id: 211,
      class_name: "pothole",
      severity: "High",
      confidence: 0.965,
      timestamp: "2026-09-15 10:48:00",
      latitude: 16.6710,
      longitude: 74.2250,
      bbox_norm: [0.29, 0.54, 0.32, 0.28],
      zone: "South Kolhapur",
      area: "Kalamba",
      street: "Kalamba Lake Ring Road (Near Jail Garden)",
      status: "reported",
      assigned_contractor: null,
      notes: null
    },
    {
      id: "rec-212",
      defect_id: 212,
      class_name: "alligator_crack",
      severity: "Medium",
      confidence: 0.873,
      timestamp: "2026-09-15 11:05:40",
      latitude: 16.6620,
      longitude: 74.2320,
      bbox_norm: [0.16, 0.45, 0.48, 0.30],
      zone: "South Kolhapur",
      area: "Morewadi",
      street: "Morewadi Phata Junction to R.K. Nagar",
      status: "inspected",
      assigned_contractor: "South Kolhapur Infra Ltd",
      notes: "Milling required across 120m stretch."
    },
    {
      id: "rec-213",
      defect_id: 213,
      class_name: "pothole",
      severity: "Medium",
      confidence: 0.862,
      timestamp: "2026-09-15 11:22:25",
      latitude: 16.6810,
      longitude: 74.2310,
      bbox_norm: [0.32, 0.58, 0.24, 0.20],
      zone: "South Kolhapur",
      area: "Kalamba",
      street: "Subhashnagar Main Connecting Road",
      status: "reported",
      assigned_contractor: null,
      notes: null
    },
    {
      id: "rec-214",
      defect_id: 214,
      class_name: "pothole",
      severity: "High",
      confidence: 0.982,
      timestamp: "2026-09-15 11:40:00",
      latitude: 16.6590,
      longitude: 74.2290,
      bbox_norm: [0.27, 0.56, 0.35, 0.30],
      zone: "South Kolhapur",
      area: "Morewadi",
      street: "Morewadi Lake Perimeter Road",
      status: "in_progress",
      assigned_contractor: "Maharastra State PWD",
      notes: "Heavy crater in bus turning radius. Rapid asphalt compaction."
    },
    {
      id: "rec-215",
      defect_id: 215,
      class_name: "alligator_crack",
      severity: "Low",
      confidence: 0.795,
      timestamp: "2026-09-15 11:58:10",
      latitude: 16.6650,
      longitude: 74.2410,
      bbox_norm: [0.22, 0.65, 0.35, 0.16],
      zone: "South Kolhapur",
      area: "Morewadi",
      street: "R.K. Nagar Housing Society Main Entrance",
      status: "repaired",
      assigned_contractor: "South Kolhapur Infra Ltd",
      notes: "Crack sealing completed."
    },
    {
      id: "rec-216",
      defect_id: 216,
      class_name: "alligator_crack",
      severity: "High",
      confidence: 0.945,
      timestamp: "2026-09-15 12:15:20",
      latitude: 16.6870,
      longitude: 74.2780,
      bbox_norm: [0.14, 0.42, 0.58, 0.38],
      zone: "East Kolhapur",
      area: "Uchgaon",
      street: "Uchgaon Phata, Near Pune-Bangalore NH48 Flyover",
      status: "reported",
      assigned_contractor: null,
      notes: null
    },
    {
      id: "rec-217",
      defect_id: 217,
      class_name: "pothole",
      severity: "High",
      confidence: 0.971,
      timestamp: "2026-09-15 12:35:45",
      latitude: 16.6450,
      longitude: 74.2810,
      bbox_norm: [0.29, 0.55, 0.34, 0.28],
      zone: "East Kolhapur",
      area: "Gokul Shirgaon",
      street: "Gokul Shirgaon MIDC Industrial Avenue Road",
      status: "in_progress",
      assigned_contractor: "MIDC Infra Contractors",
      notes: "Heavy vehicle traffic caused severe asphalt displacement."
    },
    {
      id: "rec-218",
      defect_id: 218,
      class_name: "alligator_crack",
      severity: "Medium",
      confidence: 0.856,
      timestamp: "2026-09-15 12:52:10",
      latitude: 16.6910,
      longitude: 74.2820,
      bbox_norm: [0.18, 0.46, 0.45, 0.28],
      zone: "East Kolhapur",
      area: "Uchgaon",
      street: "NH48 Highway Service Road (Uchgaon side)",
      status: "inspected",
      assigned_contractor: "NHAI Road Maintenance",
      notes: "Pavement fatigue documented during dashcam run."
    },
    {
      id: "rec-219",
      defect_id: 219,
      class_name: "pothole",
      severity: "Medium",
      confidence: 0.835,
      timestamp: "2026-09-15 13:10:00",
      latitude: 16.6410,
      longitude: 74.2750,
      bbox_norm: [0.33, 0.60, 0.22, 0.18],
      zone: "East Kolhapur",
      area: "Gokul Shirgaon",
      street: "Gokul Shirgaon Central Bus Stand Road",
      status: "reported",
      assigned_contractor: null,
      notes: null
    },
    {
      id: "rec-220",
      defect_id: 220,
      class_name: "pothole",
      severity: "Low",
      confidence: 0.812,
      timestamp: "2026-09-15 13:28:30",
      latitude: 16.6830,
      longitude: 74.2740,
      bbox_norm: [0.45, 0.68, 0.14, 0.11],
      zone: "East Kolhapur",
      area: "Uchgaon",
      street: "Uchgaon Grampanchayat Connecting Road",
      status: "repaired",
      assigned_contractor: "Rural Road Pavements",
      notes: "Cold mix patching completed."
    },
    {
      id: "rec-221",
      defect_id: 221,
      class_name: "pothole",
      severity: "High",
      confidence: 0.985,
      timestamp: "2026-09-15 13:45:15",
      latitude: 16.6910,
      longitude: 74.2140,
      bbox_norm: [0.28, 0.54, 0.35, 0.30],
      zone: "West Kolhapur",
      area: "Rankala",
      street: "Rankala Lake Chowpatty Ring Road (Near Sandhya Math)",
      status: "reported",
      assigned_contractor: null,
      notes: null
    },
    {
      id: "rec-222",
      defect_id: 222,
      class_name: "alligator_crack",
      severity: "High",
      confidence: 0.938,
      timestamp: "2026-09-15 14:02:40",
      latitude: 16.6980,
      longitude: 74.1950,
      bbox_norm: [0.12, 0.40, 0.62, 0.42],
      zone: "West Kolhapur",
      area: "Phulewadi",
      street: "Phulewadi Ring Road (Towards Balinge / Gargoti)",
      status: "inspected",
      assigned_contractor: "West Zone Civic Works",
      notes: "Base degradation spanning dual carriage lanes."
    },
    {
      id: "rec-223",
      defect_id: 223,
      class_name: "pothole",
      severity: "Medium",
      confidence: 0.884,
      timestamp: "2026-09-15 14:20:10",
      latitude: 16.6860,
      longitude: 74.2180,
      bbox_norm: [0.34, 0.58, 0.22, 0.19],
      zone: "West Kolhapur",
      area: "Rankala",
      street: "Padmashree Dr. D.Y. Patil Road, Rankala South",
      status: "in_progress",
      assigned_contractor: "Rankala Heritage Pavements",
      notes: "Emergency cold asphalt patch en route."
    },
    {
      id: "rec-224",
      defect_id: 224,
      class_name: "alligator_crack",
      severity: "Medium",
      confidence: 0.842,
      timestamp: "2026-09-15 14:38:25",
      latitude: 16.7020,
      longitude: 74.1910,
      bbox_norm: [0.20, 0.48, 0.44, 0.28],
      zone: "West Kolhapur",
      area: "Phulewadi",
      street: "Phulewadi 5th Stop City Bus Route",
      status: "reported",
      assigned_contractor: null,
      notes: null
    },
    {
      id: "rec-225",
      defect_id: 225,
      class_name: "pothole",
      severity: "Low",
      confidence: 0.801,
      timestamp: "2026-09-15 14:55:00",
      latitude: 16.6890,
      longitude: 74.2080,
      bbox_norm: [0.42, 0.69, 0.15, 0.10],
      zone: "West Kolhapur",
      area: "Rankala",
      street: "Rankala West Promenade Service Lane",
      status: "repaired",
      assigned_contractor: "Rankala Heritage Pavements",
      notes: "Repaved on 2026-09-15."
    }
  ];

  // DOM Elements
  const els = {
    // Header
    connectionPill: document.getElementById('connection-pill'),
    connectionStatusText: document.getElementById('connection-status-text'),
    officerBadge: document.getElementById('officer-badge'),
    officerTitleDisplay: document.getElementById('officer-title-display'),
    officerAreasDisplay: document.getElementById('officer-areas-display'),
    headerZoneSelect: document.getElementById('header-zone-select'),
    btnOpenModalIcon: document.getElementById('btn-open-modal-icon'),
    btnSwitchZone: document.getElementById('btn-switch-zone'),
    btnThemeToggle: document.getElementById('btn-theme-toggle'),
    themeToggleText: document.getElementById('theme-toggle-text'),
    themeToggleIcon: document.getElementById('theme-toggle-icon'),
    btnSeedData: document.getElementById('btn-seed-data'),
    btnExportReport: document.getElementById('btn-export-report'),
    // KPI Cards
    kpiTotal: document.getElementById('kpi-total-defects'),
    kpiPotholes: document.getElementById('kpi-potholes'),
    kpiAlligator: document.getElementById('kpi-alligator'),
    kpiHighPriority: document.getElementById('kpi-high-priority'),
    defectsCountBadge: document.getElementById('defects-count-badge'),
    // Filters & Worklist
    defectsListContainer: document.getElementById('defects-list-container'),
    searchDefects: document.getElementById('search-defects'),
    selectZone: document.getElementById('select-zone'),
    selectSeverity: document.getElementById('select-severity'),
    selectStatus: document.getElementById('select-status'),
    mapContainer: document.getElementById('leaflet-map'),
    basemapSelector: document.getElementById('basemap-selector'),
    btnBasemapGoogleRoad: document.getElementById('btn-basemap-google-road'),
    btnBasemapGoogleSat: document.getElementById('btn-basemap-google-sat'),
    btnBasemapOsm: document.getElementById('btn-basemap-osm'),
    mapAll: document.getElementById('filter-map-all'),
    mapPotholes: document.getElementById('filter-map-potholes'),
    mapCracks: document.getElementById('filter-map-cracks'),
    mapHigh: document.getElementById('filter-map-high'),
    // Inspection Modal
    modal: document.getElementById('inspection-modal'),
    modalTitle: document.getElementById('modal-defect-title'),
    modalSubtitle: document.getElementById('modal-defect-subtitle'),
    modalCloseBtn: document.getElementById('btn-close-modal'),
    modalRoadPreview: document.getElementById('modal-road-preview'),
    modalBboxPreview: document.getElementById('modal-bbox-preview'),
    modalBboxTag: document.getElementById('modal-bbox-tag'),
    modalCameraInfo: document.getElementById('modal-camera-info'),
    modalGpsInfo: document.getElementById('modal-gps-info'),
    formSeverity: document.getElementById('form-defect-severity'),
    formConfidence: document.getElementById('form-defect-confidence'),
    formStatus: document.getElementById('form-defect-status'),
    formContractor: document.getElementById('form-contractor'),
    formNotes: document.getElementById('form-notes'),
    modalMapsLink: document.getElementById('modal-maps-link'),
    btnSaveModal: document.getElementById('btn-save-modal'),
    // Login Modal
    zoneLoginModal: document.getElementById('zone-login-modal'),
    btnCloseLoginModal: document.getElementById('btn-close-login-modal'),
    btnConfirmLogin: document.getElementById('btn-confirm-login'),
    loginZoneDropdown: document.getElementById('login-zone-dropdown'),
    loginOfficerName: document.getElementById('login-officer-name'),
    // Patrol HUD Elements
    btnOpenPatrol: document.getElementById('btn-open-patrol'),
    patrolModal: document.getElementById('patrol-modal'),
    btnClosePatrol: document.getElementById('btn-close-patrol'),
    patrolVideo: document.getElementById('patrol-video-element'),
    patrolCanvas: document.getElementById('patrol-overlay-canvas'),
    btnPatrolPlay: document.getElementById('btn-patrol-play'),
    btnPatrolPause: document.getElementById('btn-patrol-pause'),
    btnPatrolReset: document.getElementById('btn-patrol-reset'),
    patrolProgress: document.getElementById('patrol-progress'),
    patrolTimeDisplay: document.getElementById('patrol-time-display'),
    inputUploadVideo: document.getElementById('input-upload-video'),
    btnWebcamToggle: document.getElementById('btn-webcam-toggle'),
    patrolFps: document.getElementById('patrol-fps'),
    patrolSpeed: document.getElementById('patrol-speed'),
    patrolDetectedCount: document.getElementById('patrol-detected-count'),
    hudHazardAlert: document.getElementById('hud-hazard-alert'),
    hudHazardText: document.getElementById('hud-hazard-text'),
    hudLocation: document.getElementById('hud-location'),
    hudTimestamp: document.getElementById('hud-timestamp'),
    hudStatus: document.getElementById('hud-status'),
    patrolEventList: document.getElementById('patrol-event-list'),
    patrolEmptyState: document.getElementById('patrol-empty-state'),
    btnSyncMapFocus: document.getElementById('btn-sync-map-focus'),
    // Mobile Camera Pairing Elements
    btnOpenMobile: document.getElementById('btn-open-mobile'),
    mobilePairModal: document.getElementById('mobile-pair-modal'),
    btnCloseMobileModal: document.getElementById('btn-close-mobile-modal'),
    mobileQrImg: document.getElementById('mobile-qr-img'),
    mobileHudUrlText: document.getElementById('mobile-hud-url-text'),
    btnCopyMobileUrl: document.getElementById('btn-copy-mobile-url')
  };

  /**
   * Switch Theme between White/Light (Default) and High-Contrast Dark
   */
  function setTheme(themeName) {
    state.currentTheme = themeName;
    localStorage.setItem(CONFIG.THEME_STORAGE_KEY, themeName);

    document.body.classList.remove('light-theme', 'dark-theme');
    document.body.classList.add(`${themeName}-theme`);

    if (els.themeToggleText) {
      els.themeToggleText.textContent = themeName === 'light' ? 'Dark Mode' : 'Light Mode';
    }

    if (els.themeToggleIcon) {
      if (themeName === 'light') {
        els.themeToggleIcon.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
      } else {
        els.themeToggleIcon.innerHTML = '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>';
      }
    }

    // Sync map-container class for dark/light styling
    if (els.mapContainer && state.currentBasemap) {
      els.mapContainer.className = `map-container basemap-${state.currentBasemap}`;
    }
  }

  /**
   * Basemap Configurations (Google Maps Roadmap, Google Satellite Hybrid, OpenStreetMap)
   * 100% Free & Open - Zero API Key, Zero Billing, Zero Watermarks
   */
  const BASEMAPS = {
    'google-roads': {
      name: 'Google Maps',
      url: 'https://mt{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
      options: {
        subdomains: ['0', '1', '2', '3'],
        attribution: '&copy; Google Maps',
        maxZoom: 20
      }
    },
    'google-satellite': {
      name: 'Google Satellite Hybrid',
      url: 'https://mt{s}.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
      options: {
        subdomains: ['0', '1', '2', '3'],
        attribution: '&copy; Google Maps Satellite',
        maxZoom: 20
      }
    },
    'osm': {
      name: 'OpenStreetMap',
      url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      options: {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
      }
    }
  };

  /**
   * Switch Map Basemap Layer (Google Roads, Google Satellite, OSM)
   */
  function setBasemap(type) {
    if (!BASEMAPS[type]) type = 'google-roads';
    state.currentBasemap = type;
    localStorage.setItem(CONFIG.BASEMAP_STORAGE_KEY, type);

    if (state.map) {
      if (state.tileLayer) {
        state.map.removeLayer(state.tileLayer);
      }
      const cfg = BASEMAPS[type];
      state.tileLayer = L.tileLayer(cfg.url, cfg.options).addTo(state.map);

      // Sync map-container class for dark theme tile filters
      if (els.mapContainer) {
        els.mapContainer.className = `map-container basemap-${type}`;
      }
    }

    // Update active UI state on basemap buttons
    document.querySelectorAll('.basemap-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.basemap === type);
    });
  }

  /**
   * Initialize Map centered on active Kolhapur Zone with Google Maps Default
   */
  function initMap() {
    if (!window.L) {
      console.error('Leaflet library not loaded.');
      return;
    }

    const currentZoneConfig = KOLHAPUR_ZONES[state.currentZone] || KOLHAPUR_ZONES['all'];
    const centerCoords = currentZoneConfig.center || CONFIG.DEFAULT_CENTER;
    const zoomLvl = currentZoneConfig.zoom || CONFIG.DEFAULT_ZOOM;

    state.map = L.map('leaflet-map', {
      center: centerCoords,
      zoom: zoomLvl,
      zoomControl: true
    });

    // Default to Google Maps (100% Free, Zero API Key Required)
    setBasemap(state.currentBasemap || 'google-roads');

    state.markersLayer = L.layerGroup().addTo(state.map);
    state.zonesLayerGroup = L.featureGroup().addTo(state.map);
    
    // Render the Kolhapur 5-Zone Operational Case Study Polygons & Markers
    loadAndRenderOperationalZones();
  }

  /**
   * KOLHAPUR 5-ZONE OPERATIONAL ROAD-DAMAGE CASE STUDY
   * Loads the single editable GeoJSON configuration, paints distinct colored semi-transparent polygons,
   * places center markers, and renders rich interactive telemetry popups.
   */
  async function loadAndRenderOperationalZones() {
    if (!state.map || !state.zonesLayerGroup) return;

    state.zonesLayerGroup.clearLayers();
    state.zoneLayers = {};
    state.zoneCenterMarkers = {};

    let geojsonData = null;
    let statsData = null;

    try {
      const [geoRes, statRes] = await Promise.all([
        fetch(`${CONFIG.API_BASE}/api/zones/geojson`).catch(() => null),
        fetch(`${CONFIG.API_BASE}/api/zones/statistics`).catch(() => null)
      ]);

      if (geoRes && geoRes.ok) {
        geojsonData = await geoRes.json();
      }
      if (statRes && statRes.ok) {
        statsData = await statRes.json();
      }
    } catch (err) {
      console.warn('Zone API sync fallback:', err);
    }

    // Fallback GeoJSON if running in purely offline/client-only environment
    if (!geojsonData) {
      geojsonData = {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            id: "central_kolhapur",
            properties: {
              zone_id: "central_kolhapur",
              zone_name: "Central Kolhapur",
              center: [16.7040, 74.2380],
              localities_str: "Shahupuri, Laxmipuri, Rajarampuri, Station Road",
              challenges: "High-density commercial transit, recurrent municipal pipeline excavation, heavy bus terminal traffic, severe asphalt fatigue cracking.",
              color: "#3b82f6",
              border_color: "#1d4ed8",
              fill_opacity: 0.28
            },
            geometry: {
              type: "Polygon",
              coordinates: [[[74.220, 16.715], [74.252, 16.715], [74.252, 16.696], [74.220, 16.696], [74.220, 16.715]]]
            }
          },
          {
            type: "Feature",
            id: "north_kolhapur",
            properties: {
              zone_id: "north_kolhapur",
              zone_name: "North Kolhapur",
              center: [16.7250, 74.2480],
              localities_str: "Ujalaiwadi, Kasaba Bawada side",
              challenges: "Panchganga river basin waterlogging during monsoon, subgrade pavement moisture saturation, asphalt edge raveling.",
              color: "#10b981",
              border_color: "#047857",
              fill_opacity: 0.28
            },
            geometry: {
              type: "Polygon",
              coordinates: [[[74.220, 16.745], [74.270, 16.745], [74.270, 16.715], [74.220, 16.715], [74.220, 16.745]]]
            }
          },
          {
            type: "Feature",
            id: "south_kolhapur",
            properties: {
              zone_id: "south_kolhapur",
              zone_name: "South Kolhapur",
              center: [16.6750, 74.2280],
              localities_str: "Kalamba, Morewadi side",
              challenges: "Rapid suburban residential expansion, heavy dumper & concrete mixer transit, unpaved shoulder breakdown, deep edge craters.",
              color: "#f59e0b",
              border_color: "#b45309",
              fill_opacity: 0.28
            },
            geometry: {
              type: "Polygon",
              coordinates: [[[74.220, 16.696], [74.252, 16.696], [74.252, 16.655], [74.220, 16.655], [74.220, 16.696]]]
            }
          },
          {
            type: "Feature",
            id: "east_kolhapur",
            properties: {
              zone_id: "east_kolhapur",
              zone_name: "East Kolhapur",
              center: [16.6850, 74.2750],
              localities_str: "Uchgaon, Gokul Shirgaon MIDC",
              challenges: "Multi-axle industrial cargo haulage, freight transport shear stresses, severe interconnected alligator mesh cracking.",
              color: "#8b5cf6",
              border_color: "#6d28d9",
              fill_opacity: 0.28
            },
            geometry: {
              type: "Polygon",
              coordinates: [[[74.252, 16.715], [74.300, 16.715], [74.300, 16.655], [74.252, 16.655], [74.252, 16.715]]]
            }
          },
          {
            type: "Feature",
            id: "west_kolhapur",
            properties: {
              zone_id: "west_kolhapur",
              zone_name: "West Kolhapur",
              center: [16.6920, 74.2050],
              localities_str: "Rankala Lake Promenade, Phulewadi",
              challenges: "High tourist vehicular density, lake perimeter moisture seepage, cobblestone-asphalt interface detachment, sharp rim-impact potholes.",
              color: "#f43f5e",
              border_color: "#be123c",
              fill_opacity: 0.28
            },
            geometry: {
              type: "Polygon",
              coordinates: [[[74.180, 16.715], [74.220, 16.715], [74.220, 16.665], [74.180, 16.665], [74.180, 16.715]]]
            }
          }
        ]
      };
    }

    state.zoneGeoJSON = geojsonData;
    state.zoneStatistics = (statsData && statsData.zones) ? statsData.zones : {};

    const features = geojsonData.features || [];

    features.forEach(feature => {
      const props = feature.properties || {};
      const zid = props.zone_id;
      const color = props.color || '#3b82f6';
      const borderColor = props.border_color || color;

      // 1. Semi-transparent Polygon Layer
      const poly = L.geoJSON(feature, {
        style: {
          color: borderColor,
          weight: props.stroke_width || 2.5,
          opacity: 0.9,
          fillColor: color,
          fillOpacity: props.fill_opacity || 0.28
        }
      });

      // Hover / Permanent tooltip
      poly.bindTooltip(`<strong>${props.zone_name}</strong>`, {
        permanent: false,
        direction: 'center',
        className: 'zone-polygon-label'
      });

      // 2. Center Marker at supplied GPS coordinates
      const centerCoords = props.center;
      const centerIcon = L.divIcon({
        className: 'custom-zone-marker-container',
        html: `<div class="zone-center-marker" style="border-color: ${borderColor}; color: ${borderColor};" title="${props.zone_name} Operational Center">🏛️</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      });
      const marker = L.marker(centerCoords, { icon: centerIcon });

      // 3. Interactive Popup Card (Name, Center, Localities, Challenges, Incident Statistics)
      function getPopupHTML() {
        // Calculate dynamic stats from state.defects if not provided by backend
        let zstats = state.zoneStatistics[zid];
        if (!zstats) {
          const matching = state.defects.filter(d => 
            (d.zone || '').toLowerCase() === (props.zone_name || '').toLowerCase() ||
            (d.zone_id || '').toLowerCase() === zid.toLowerCase()
          );
          zstats = {
            total_incidents: matching.length,
            potholes: matching.filter(d => (d.class_name || '').toLowerCase() === 'pothole').length,
            alligator_cracks: matching.filter(d => (d.class_name || '').toLowerCase().includes('crack')).length,
            severity: {
              High: matching.filter(d => (d.severity || '').toLowerCase() === 'high').length,
              Medium: matching.filter(d => (d.severity || '').toLowerCase() === 'medium').length,
              Low: matching.filter(d => (d.severity || '').toLowerCase() === 'low').length
            },
            status: {
              reported: matching.filter(d => (d.status || '').toLowerCase() === 'reported').length,
              repaired: matching.filter(d => (d.status || '').toLowerCase() === 'repaired').length
            }
          };
        }

        return `
          <div class="zone-popup-card">
            <div class="zone-popup-header">
              <span class="zone-popup-swatch" style="background: ${color};"></span>
              <h4 class="zone-popup-title">${props.zone_name}</h4>
              <span class="zone-popup-badge">OPERATIONAL ZONE</span>
            </div>
            <div class="zone-popup-meta">
              <div><strong>Center GPS:</strong> ${centerCoords[0].toFixed(4)}° N, ${centerCoords[1].toFixed(4)}° E</div>
              <div><strong>Localities:</strong> ${props.localities_str || (props.localities || []).join(', ')}</div>
              <div style="margin-top: 5px;"><strong>Regional Distress Challenges:</strong> ${props.challenges}</div>
            </div>
            <div class="zone-stats-grid">
              <div class="zstat-box">
                <span class="zstat-val">${zstats.total_incidents}</span>
                <span class="zstat-lbl">Incidents</span>
              </div>
              <div class="zstat-box">
                <span class="zstat-val" style="color: #ef4444;">${zstats.severity ? zstats.severity.High : 0}</span>
                <span class="zstat-lbl">High Risk</span>
              </div>
              <div class="zstat-box">
                <span class="zstat-val" style="color: #10b981;">${zstats.status ? zstats.status.repaired : 0}</span>
                <span class="zstat-lbl">Repaired</span>
              </div>
            </div>
            <div style="margin-bottom: 8px;">
              <button class="btn btn-secondary btn-block" style="font-size: 0.74rem; padding: 6px 12px; width: 100%;" onclick="window.selectZoneFromMap('${props.zone_name}')">
                🔍 Filter Dashboard to ${props.zone_name}
              </button>
            </div>
            <div class="zone-popup-disclaimer">
              ⚠️ Project-defined operational zone for regional case-study analysis; not an official KMC legal ward boundary.
            </div>
          </div>
        `;
      }

      poly.bindPopup(getPopupHTML, { maxWidth: 310 });
      marker.bindPopup(getPopupHTML, { maxWidth: 310 });

      poly.addTo(state.zonesLayerGroup);
      marker.addTo(state.zonesLayerGroup);

      state.zoneLayers[zid] = poly;
      state.zoneCenterMarkers[zid] = marker;
    });

    updateZoneHighlights();
  }

  function updateZoneHighlights() {
    if (!state.zoneLayers) return;
    const cur = (state.currentZone || '').toLowerCase().replace(/ /g, '_');

    Object.keys(state.zoneLayers).forEach(zid => {
      const poly = state.zoneLayers[zid];
      if (!poly) return;

      if (cur === 'all' || !cur) {
        poly.setStyle({ fillOpacity: 0.25, weight: 2.5, opacity: 0.85 });
      } else if (zid === cur || zid.replace(/_/g, ' ') === cur) {
        poly.setStyle({ fillOpacity: 0.48, weight: 4.0, opacity: 1.0 });
      } else {
        poly.setStyle({ fillOpacity: 0.10, weight: 1.5, opacity: 0.45 });
      }
    });
  }

  // Global callback for popup filter button
  window.selectZoneFromMap = function(zoneName) {
    selectZone(zoneName);
  };


  /**
   * Area/Zone Authentication & Management (Zero API Dependency)
   */
  function selectZone(zoneKey) {
    if (!zoneKey) return;
    state.currentZone = zoneKey;
    state.isLoggedIn = true;
    localStorage.setItem(CONFIG.ZONE_STORAGE_KEY, zoneKey);
    localStorage.setItem(CONFIG.AUTH_STORAGE_KEY, 'true');

    const zoneInfo = KOLHAPUR_ZONES[zoneKey] || KOLHAPUR_ZONES['all'];
    
    // Sync all dropdowns: header, filter bar, and modal
    if (els.headerZoneSelect && els.headerZoneSelect.value !== zoneKey) {
      els.headerZoneSelect.value = zoneKey;
    }
    if (els.selectZone && els.selectZone.value !== zoneKey) {
      els.selectZone.value = zoneKey;
    }
    if (els.loginZoneDropdown && els.loginZoneDropdown.value !== zoneKey) {
      els.loginZoneDropdown.value = zoneKey;
    }

    // Update navbar badge text
    if (els.officerTitleDisplay) {
      els.officerTitleDisplay.textContent = zoneInfo.title;
    }
    if (els.officerAreasDisplay) {
      els.officerAreasDisplay.textContent = zoneInfo.areas;
    }

    // Fly map smoothly to zone coordinates
    if (state.map && zoneInfo.center) {
      state.map.flyTo(zoneInfo.center, zoneInfo.zoom, { duration: 1.2 });
    }

    // Update active highlight in cards
    document.querySelectorAll('.zone-select-card').forEach(c => {
      c.classList.toggle('active-zone', c.getAttribute('data-zone') === zoneKey);
    });

    closeLoginModal();
    applyFilters();
    updateZoneHighlights();

    // Show instant visual confirmation
    showToast(`📍 <strong>Active Zone:</strong> ${zoneInfo.name || zoneKey}`);

    // Asynchronously notify backend if online - NEVER blocks UI!
    if (state.backendOnline) {
      fetch(`${CONFIG.API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zone: zoneKey })
      }).catch(err => console.debug('Zone login sync note:', err));
    }
  }

  /**
   * Cycle to Next Kolhapur Area (Central -> North -> South -> East -> West -> Citywide)
   */
  function cycleNextZone() {
    const currentIndex = ZONE_KEYS.indexOf(state.currentZone);
    const nextIndex = (currentIndex + 1) % ZONE_KEYS.length;
    const nextZone = ZONE_KEYS[nextIndex];
    selectZone(nextZone);
  }

  let toastTimer = null;
  function showToast(msg) {
    const el = document.getElementById('toast-notification');
    if (!el) return;
    el.innerHTML = msg;
    el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      el.classList.remove('show');
    }, 2500);
  }

  function openLoginModal() {
    if (els.zoneLoginModal) {
      els.zoneLoginModal.style.display = 'flex';
      // Sync active state in modal cards
      document.querySelectorAll('.zone-select-card').forEach(c => {
        c.classList.toggle('active-zone', c.getAttribute('data-zone') === state.currentZone);
      });
      if (els.loginZoneDropdown) {
        els.loginZoneDropdown.value = state.currentZone;
      }
    }
  }

  function closeModal() {
    if (els.modal) {
      els.modal.style.display = 'none';
      state.selectedDefect = null;
    }
  }

  function closeLoginModal() {
    if (els.zoneLoginModal) {
      els.zoneLoginModal.style.display = 'none';
    }
  }

  /**
   * Check Backend Health and Fetch Data (Zero-API Resilient)
   */
  async function loadData() {
    try {
      const healthRes = await fetch(`${CONFIG.API_BASE}/api/health`, { method: 'GET', signal: AbortSignal.timeout(1800) });
      if (healthRes.ok) {
        state.backendOnline = true;
        updateConnectionStatus(true);
        const dataRes = await fetch(`${CONFIG.API_BASE}/api/defects?limit=500`);
        const records = await dataRes.json();
        
        if (records && records.length > 0) {
          state.defects = records;
        } else {
          // If DB is empty, auto-seed with local sample
          state.defects = loadCachedOrDefault();
          saveLocalCache(state.defects);
        }
      } else {
        throw new Error('Backend responded with error');
      }
    } catch (e) {
      console.info('Operating in self-contained client mode with local Kolhapur telemetry.', e.message);
      state.backendOnline = false;
      updateConnectionStatus(false);
      state.defects = loadCachedOrDefault();
    }

    applyFilters();
  }

  function updateConnectionStatus(isOnline) {
    if (isOnline) {
      els.connectionPill.style.background = 'rgba(16, 185, 129, 0.12)';
      els.connectionPill.style.borderColor = 'rgba(16, 185, 129, 0.35)';
      els.connectionStatusText.textContent = 'Live Ingestion (API Online)';
      els.connectionStatusText.style.color = '#34d399';
    } else {
      els.connectionPill.style.background = 'rgba(6, 182, 212, 0.12)';
      els.connectionPill.style.borderColor = 'rgba(6, 182, 212, 0.35)';
      els.connectionStatusText.textContent = 'Local Telemetry Active';
      els.connectionStatusText.style.color = '#22d3ee';
    }
  }

  function loadCachedOrDefault() {
    const cached = localStorage.getItem(CONFIG.STORAGE_KEY);
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      } catch (err) {
        console.warn('Invalid cache payload:', err);
      }
    }
    return JSON.parse(JSON.stringify(DEFAULT_SAMPLE_DEFECTS));
  }

  function saveLocalCache(defects) {
    localStorage.setItem(CONFIG.STORAGE_KEY, JSON.stringify(defects));
  }

  /**
   * Filter and Search Pipeline (Area / Zone Isolated)
   */
  function applyFilters() {
    let list = [...state.defects];

    // 1. Zone Isolation Filter (Scopes by zone_id, zone_name, or zone alias)
    if (state.currentZone && state.currentZone.toLowerCase() !== 'all') {
      const target = state.currentZone.toLowerCase();
      const targetId = target.replace(/ /g, '_');
      list = list.filter(d => 
        (d.zone || '').toLowerCase() === target ||
        (d.zone_name || '').toLowerCase() === target ||
        (d.zone_id || '').toLowerCase() === targetId ||
        (d.zone_id || '').toLowerCase() === target
      );
    }

    // 2. Map Quick Filter
    if (state.activeFilter === 'potholes') {
      list = list.filter(d => (d.class_name || '').toLowerCase() === 'pothole');
    } else if (state.activeFilter === 'cracks') {
      list = list.filter(d => (d.class_name || '').toLowerCase().includes('crack'));
    } else if (state.activeFilter === 'high') {
      list = list.filter(d => (d.severity || '').toLowerCase() === 'high');
    }

    // 3. Dropdown Severity Filter
    if (state.selectedSeverity) {
      list = list.filter(d => (d.severity || '').toLowerCase() === state.selectedSeverity.toLowerCase());
    }

    // 4. Dropdown Status Filter
    if (state.selectedStatus) {
      list = list.filter(d => (d.status || '').toLowerCase() === state.selectedStatus.toLowerCase());
    }

    // 5. Text Search (ID, area, street, or class)
    if (state.searchQuery.trim()) {
      const q = state.searchQuery.trim().toLowerCase();
      list = list.filter(d => {
        const idStr = String(d.defect_id || d.id || '');
        const cName = (d.class_name || '').toLowerCase();
        const area = (d.area || '').toLowerCase();
        const street = (d.street || '').toLowerCase();
        const zone = (d.zone || '').toLowerCase();
        return idStr.includes(q) || cName.includes(q) || area.includes(q) || street.includes(q) || zone.includes(q);
      });
    }

    state.filteredDefects = list;
    updateKPIs();
    renderMapMarkers();
    renderTriageList();
  }

  /**
   * Update KPI Cards (Zone-specific aggregation)
   */
  function updateKPIs() {
    const zonePool = (state.currentZone && state.currentZone.toLowerCase() !== 'all')
      ? state.defects.filter(d => (d.zone || '').toLowerCase() === state.currentZone.toLowerCase())
      : state.defects;

    const total = zonePool.length;
    const potholes = zonePool.filter(d => (d.class_name || '').toLowerCase() === 'pothole').length;
    const cracks = zonePool.filter(d => (d.class_name || '').toLowerCase().includes('crack')).length;
    const high = zonePool.filter(d => (d.severity || '').toLowerCase() === 'high').length;

    els.kpiTotal.textContent = total;
    els.kpiPotholes.textContent = potholes;
    els.kpiAlligator.textContent = cracks;
    els.kpiHighPriority.textContent = high;
    
    const zoneLabel = state.currentZone === 'all' ? 'All Kolhapur City' : state.currentZone;
    els.defectsCountBadge.textContent = `${state.filteredDefects.length} in ${zoneLabel}`;
  }

  /**
   * Render Leaflet Markers
   */
  function renderMapMarkers() {
    if (!state.map || !state.markersLayer) return;
    state.markersLayer.clearLayers();

    state.filteredDefects.forEach(defect => {
      const lat = defect.latitude || (defect.gps && defect.gps.latitude);
      const lng = defect.longitude || (defect.gps && defect.gps.longitude);
      if (lat == null || lng == null) return;

      const severity = defect.severity || 'Medium';
      let pinColor = '#d97706';
      let fillColor = 'rgba(217, 119, 6, 0.4)';

      if (defect.status === 'repaired') {
        pinColor = '#059669';
        fillColor = 'rgba(5, 150, 105, 0.4)';
      } else if (severity.toLowerCase() === 'high') {
        pinColor = '#dc2626';
        fillColor = 'rgba(220, 38, 38, 0.5)';
      } else if (severity.toLowerCase() === 'low') {
        pinColor = '#059669';
        fillColor = 'rgba(5, 150, 105, 0.4)';
      }

      const marker = L.circleMarker([lat, lng], {
        radius: severity.toLowerCase() === 'high' ? 9 : 7,
        color: pinColor,
        weight: 2.5,
        fillColor: fillColor,
        fillOpacity: 0.85
      });

      const areaText = defect.area || defect.zone || 'Kolhapur';
      const streetText = defect.street || 'Municipal Road';

      const popupContent = `
        <div class="popup-title">#${defect.defect_id || defect.id} ${defect.class_name.toUpperCase()}</div>
        <div class="popup-meta">
          <span><strong>Zone:</strong> ${defect.zone || 'Central Kolhapur'}</span>
          <span><strong>Locality:</strong> ${areaText}</span>
          <span><strong>Street:</strong> ${streetText}</span>
          <span><strong>Severity:</strong> ${severity}</span>
          <span><strong>Status:</strong> ${defect.status || 'reported'}</span>
        </div>
        <button class="popup-btn" onclick="window.inspectDefect('${defect.id || defect.defect_id}')">Inspect &amp; Dispatch</button>
      `;

      marker.bindPopup(popupContent);
      marker.defectData = defect;
      state.markersLayer.addLayer(marker);
    });
  }

  /**
   * Render Triage List Cards
   */
  function renderTriageList() {
    els.defectsListContainer.innerHTML = '';

    if (state.filteredDefects.length === 0) {
      els.defectsListContainer.innerHTML = `
        <div class="empty-state">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <p>No road distress items found for ${state.currentZone === 'all' ? 'Kolhapur' : state.currentZone} with active filters.</p>
        </div>
      `;
      return;
    }

    state.filteredDefects.forEach(defect => {
      const card = document.createElement('div');
      const severity = defect.severity || 'Medium';
      const status = defect.status || 'reported';
      const cname = defect.class_name === 'pothole' ? 'Pothole' : 'Alligator Crack';
      const confPercent = Math.round((defect.confidence || 0.85) * 100);
      const street = defect.street || 'Municipal Road';
      const area = defect.area || defect.zone || 'Kolhapur';

      card.className = `defect-card card-severity-${severity}`;
      card.id = `card-defect-${defect.id || defect.defect_id}`;

      let statusBadgeClass = 'badge-warning';
      if (status === 'repaired') statusBadgeClass = 'badge-success';
      else if (status === 'in_progress') statusBadgeClass = 'badge-cyan';
      else if (status === 'inspected') statusBadgeClass = 'badge-neutral';

      card.innerHTML = `
        <div class="defect-card-header">
          <div class="defect-title-wrap">
            <span class="defect-title">#${defect.defect_id || defect.id} ${cname}</span>
            <span class="defect-location">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
              ${street} &bull; <strong>${area}</strong>
            </span>
          </div>
          <div class="defect-badge-group">
            <span class="badge ${severity === 'High' ? 'badge-critical' : (severity === 'Medium' ? 'badge-warning' : 'badge-success')}">${severity}</span>
            <span class="badge ${statusBadgeClass}">${status}</span>
          </div>
        </div>
        <div class="defect-meta-row">
          <span class="defect-meta-item">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            ${defect.timestamp ? defect.timestamp.split(' ')[1] || defect.timestamp : '10:00:00'}
          </span>
          <span class="defect-meta-item">Conf: ${confPercent}%</span>
          <button class="defect-action-btn" data-id="${defect.id || defect.defect_id}">Inspect</button>
        </div>
      `;

      card.addEventListener('click', (e) => {
        if (e.target.closest('.defect-action-btn')) return;
        focusOnDefect(defect);
      });

      const inspectBtn = card.querySelector('.defect-action-btn');
      inspectBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        openInspectionModal(defect);
      });

      els.defectsListContainer.appendChild(card);
    });
  }

  /**
   * Pan Map and Highlight Card
   */
  function focusOnDefect(defect) {
    const lat = defect.latitude || (defect.gps && defect.gps.latitude);
    const lng = defect.longitude || (defect.gps && defect.gps.longitude);
    if (lat != null && lng != null && state.map) {
      state.map.flyTo([lat, lng], 16, { duration: 1.2 });
    }

    document.querySelectorAll('.defect-card').forEach(c => c.classList.remove('active-selected'));
    const targetCard = document.getElementById(`card-defect-${defect.id || defect.defect_id}`);
    if (targetCard) {
      targetCard.classList.add('active-selected');
      targetCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  /**
   * Open Inspection Modal
   */
  function openInspectionModal(defect) {
    state.selectedDefect = defect;
    const cname = defect.class_name === 'pothole' ? 'Pothole' : 'Alligator Cracking';
    const id = defect.defect_id || defect.id;
    const lat = defect.latitude || (defect.gps && defect.gps.latitude);
    const lng = defect.longitude || (defect.gps && defect.gps.longitude);
    const conf = Math.round((defect.confidence || 0.85) * 100);

    els.modalTitle.textContent = `Kolhapur Defect Inspection #${id}`;
    els.modalSubtitle.textContent = `${cname} verified on ${defect.street || 'Kolhapur Road'} (${defect.area || defect.zone})`;
    els.formSeverity.value = defect.severity || 'Medium';
    els.formConfidence.value = `${conf}% detector confidence`;
    els.formStatus.value = defect.status || 'reported';
    els.formContractor.value = defect.assigned_contractor || '';
    els.formNotes.value = defect.notes || '';

    // Sensor & GPS Bar
    els.modalCameraInfo.textContent = `Sensor: DashCam-01 | Model: YOLO11n | Zone: ${defect.zone || 'Central'}`;
    els.modalGpsInfo.textContent = `GPS: ${lat.toFixed(4)}° N, ${lng.toFixed(4)}° E (Kolhapur)`;

    // Google Maps link (Standard clean web URL, zero API key required)
    els.modalMapsLink.href = `https://www.google.com/maps?q=${lat},${lng}`;

    // Render visual bounding box
    const bbox = defect.bbox_norm || [0.3, 0.5, 0.3, 0.25];
    const leftPct = (bbox[0] * 100).toFixed(1);
    const topPct = (bbox[1] * 100).toFixed(1);
    const widthPct = (bbox[2] * 100).toFixed(1);
    const heightPct = (bbox[3] * 100).toFixed(1);

    els.modalBboxPreview.style.left = `${leftPct}%`;
    els.modalBboxPreview.style.top = `${topPct}%`;
    els.modalBboxPreview.style.width = `${widthPct}%`;
    els.modalBboxPreview.style.height = `${heightPct}%`;
    els.modalBboxTag.textContent = `${defect.class_name.toUpperCase()} ${conf}%`;

    const isHigh = (defect.severity || '').toLowerCase() === 'high';
    const tagColor = isHigh ? 'var(--severity-critical)' : 'var(--severity-warning)';
    els.modalBboxPreview.style.borderColor = tagColor;
    els.modalBboxTag.style.backgroundColor = tagColor;

    els.modal.style.display = 'flex';
  }

  /**
   * Save Inspection & Municipal Workflow Update
   */
  async function saveDefectUpdate() {
    if (!state.selectedDefect) return;

    const newStatus = els.formStatus.value;
    const contractor = els.formContractor.value.trim();
    const notes = els.formNotes.value.trim();

    const defectId = state.selectedDefect.id || state.selectedDefect.defect_id;

    if (state.backendOnline) {
      try {
        await fetch(`${CONFIG.API_BASE}/api/defects/${defectId}/status`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            status: newStatus,
            assigned_contractor: contractor || null,
            notes: notes || null
          })
        });
      } catch (err) {
        console.warn('Could not sync update to API backend:', err);
      }
    }

    state.selectedDefect.status = newStatus;
    state.selectedDefect.assigned_contractor = contractor || null;
    state.selectedDefect.notes = notes || null;

    const idx = state.defects.findIndex(d => (d.id || d.defect_id) === defectId);
    if (idx !== -1) {
      state.defects[idx].status = newStatus;
      state.defects[idx].assigned_contractor = contractor || null;
      state.defects[idx].notes = notes || null;
    }

    saveLocalCache(state.defects);
    closeModal();
    applyFilters();
  }

  /**
   * Seed / Load Detections
   */
  async function seedLiveDetections() {
    if (state.backendOnline) {
      try {
        const res = await fetch(`${CONFIG.API_BASE}/api/defects/seed_sample`, { method: 'POST' });
        if (res.ok) {
          const freshData = await fetch(`${CONFIG.API_BASE}/api/defects?limit=500`);
          state.defects = await freshData.json();
          applyFilters();
          alert('Successfully seeded 25 Kolhapur road distress events into active database!');
          return;
        }
      } catch (e) {
        console.warn('API seed failed:', e);
      }
    }

    state.defects = JSON.parse(JSON.stringify(DEFAULT_SAMPLE_DEFECTS));
    saveLocalCache(state.defects);
    applyFilters();
    alert('Loaded full suite of verified Kolhapur road distress events into active dashboard.');
  }

  /**
   * Export Municipal Report (JSON / CSV)
   */
  function exportMunicipalReport() {
    const exportData = state.filteredDefects.map(d => ({
      defect_id: d.defect_id || d.id,
      zone: d.zone || state.currentZone,
      area: d.area || 'N/A',
      street: d.street || 'N/A',
      class: d.class_name,
      severity: d.severity,
      confidence: d.confidence,
      status: d.status,
      timestamp: d.timestamp,
      latitude: d.latitude || (d.gps && d.gps.latitude),
      longitude: d.longitude || (d.gps && d.gps.longitude),
      contractor: d.assigned_contractor || 'Unassigned',
      notes: d.notes || ''
    }));

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `kolhapur_road_damage_report_${state.currentZone.replace(/\s+/g, '_')}_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  /* ==========================================================================
     Autonomous Dashcam Patrol & Edge AI Real-Time Stream Engine
     ========================================================================== */

  const DEFAULT_PATROL_ROUTE = {
    unit_id: "KMC-PATROL-04",
    zone: "Central Kolhapur",
    route_name: "Station Road Shahupuri -> Rajarampuri Arterial Survey",
    video_url: "/media/dashcam_demo.mp4",
    total_duration_sec: 31.0,
    base_speed_kmh: 36.0,
    waypoints: [
      { time_sec: 0.0, lat: 16.7042, lng: 74.2395, street: "Station Road (Shahupuri Bus Stand)" },
      { time_sec: 5.0, lat: 16.7049, lng: 74.2412, street: "Station Road (Railway Overbridge)" },
      { time_sec: 10.0, lat: 16.7057, lng: 74.2429, street: "Station Road (Shahupuri Corner)" },
      { time_sec: 15.0, lat: 16.7064, lng: 74.2446, street: "Laxmipuri Link Road" },
      { time_sec: 20.0, lat: 16.7071, lng: 74.2462, street: "Rajarampuri 1st Lane Junction" },
      { time_sec: 25.0, lat: 16.7078, lng: 74.2477, street: "Rajarampuri 2nd Lane Main" },
      { time_sec: 31.0, lat: 16.7085, lng: 74.2492, street: "Rajarampuri Main Road" }
    ],
    events: [
      {
        time_sec: 3.2,
        duration: 3.2,
        defect_id: "PATROL-101",
        class_name: "pothole",
        severity: "High",
        confidence: 0.942,
        gps: { latitude: 16.7046, longitude: 74.2405 },
        zone: "Central Kolhapur",
        area: "Shahupuri",
        street: "Station Road (Shahupuri Bus Stand)",
        bbox_norm: [0.34, 0.56, 0.28, 0.24],
        notes: "Deep impact crater in vehicle travel wheel path."
      },
      {
        time_sec: 8.5,
        duration: 3.5,
        defect_id: "PATROL-102",
        class_name: "alligator_crack",
        severity: "Medium",
        confidence: 0.885,
        gps: { latitude: 16.7055, longitude: 74.2425 },
        zone: "Central Kolhapur",
        area: "Shahupuri",
        street: "Station Road (Railway Overbridge)",
        bbox_norm: [0.18, 0.58, 0.44, 0.26],
        notes: "Interconnected fatigue mesh cracking across lane center."
      },
      {
        time_sec: 15.8,
        duration: 3.6,
        defect_id: "PATROL-103",
        class_name: "pothole",
        severity: "High",
        confidence: 0.961,
        gps: { latitude: 16.7065, longitude: 74.2448 },
        zone: "Central Kolhapur",
        area: "Laxmipuri",
        street: "Laxmipuri Link Road",
        bbox_norm: [0.42, 0.52, 0.32, 0.26],
        notes: "Severe structural asphalt cavity causing traffic deceleration."
      },
      {
        time_sec: 22.4,
        duration: 3.2,
        defect_id: "PATROL-104",
        class_name: "pothole",
        severity: "Medium",
        confidence: 0.849,
        gps: { latitude: 16.7074, longitude: 74.2468 },
        zone: "Central Kolhapur",
        area: "Rajarampuri",
        street: "Rajarampuri 1st Lane Junction",
        bbox_norm: [0.26, 0.62, 0.24, 0.20],
        notes: "Surface pit with loose aggregate gravel scatter."
      },
      {
        time_sec: 27.5,
        duration: 3.5,
        defect_id: "PATROL-105",
        class_name: "alligator_crack",
        severity: "High",
        confidence: 0.923,
        gps: { latitude: 16.7082, longitude: 74.2485 },
        zone: "Central Kolhapur",
        area: "Rajarampuri",
        street: "Rajarampuri 2nd Lane Main",
        bbox_norm: [0.16, 0.50, 0.52, 0.34],
        notes: "Heavy fatigue cracking indicating subgrade moisture ingress."
      }
    ]
  };

  const patrolState = {
    routeData: DEFAULT_PATROL_ROUTE,
    isPlaying: false,
    currentTime: 0,
    duration: 31.0,
    detectedEventIds: new Set(),
    vehicleMarker: null,
    webcamStream: null,
    isWebcam: false,
    animFrameId: null,
    hazardTimeout: null
  };

  async function loadPatrolRoute() {
    try {
      const res = await fetch(`${CONFIG.API_BASE}/api/patrol/route?zone=${encodeURIComponent(state.currentZone)}`, {
        signal: AbortSignal.timeout(2000)
      });
      if (res.ok) {
        const data = await res.json();
        patrolState.routeData = data;
        if (data.total_duration_sec) patrolState.duration = data.total_duration_sec;
      }
    } catch (err) {
      console.info('Using pre-calibrated Kolhapur municipal patrol route.', err);
      patrolState.routeData = DEFAULT_PATROL_ROUTE;
    }
  }

  function openPatrolModal() {
    if (!els.patrolModal) return;
    els.patrolModal.style.display = 'flex';

    if (!patrolState.routeData) loadPatrolRoute();

    // Prepare video source if not set
    if (els.patrolVideo && !els.patrolVideo.src && !patrolState.isWebcam) {
      els.patrolVideo.src = `${CONFIG.API_BASE}/media/dashcam_demo.mp4`;
      els.patrolVideo.load();
    }
  }

  function closePatrolModal() {
    if (!els.patrolModal) return;
    pausePatrol();
    els.patrolModal.style.display = 'none';
  }

  function getPatrolPosition(timeSec) {
    const waypoints = (patrolState.routeData && patrolState.routeData.waypoints) || DEFAULT_PATROL_ROUTE.waypoints;
    if (timeSec <= waypoints[0].time_sec) return waypoints[0];
    if (timeSec >= waypoints[waypoints.length - 1].time_sec) return waypoints[waypoints.length - 1];

    for (let i = 0; i < waypoints.length - 1; i++) {
      const w1 = waypoints[i];
      const w2 = waypoints[i + 1];
      if (timeSec >= w1.time_sec && timeSec <= w2.time_sec) {
        const factor = (timeSec - w1.time_sec) / (w2.time_sec - w1.time_sec);
        return {
          lat: w1.lat + (w2.lat - w1.lat) * factor,
          lng: w1.lng + (w2.lng - w1.lng) * factor,
          street: w1.street
        };
      }
    }
    return waypoints[0];
  }

  function renderPatrolOverlay(activeEvents) {
    if (!els.patrolCanvas || !els.patrolVideo) return;
    const ctx = els.patrolCanvas.getContext('2d');
    if (!ctx) return;

    const w = els.patrolVideo.videoWidth || els.patrolVideo.clientWidth || 640;
    const h = els.patrolVideo.videoHeight || els.patrolVideo.clientHeight || 480;

    if (els.patrolCanvas.width !== w || els.patrolCanvas.height !== h) {
      els.patrolCanvas.width = w;
      els.patrolCanvas.height = h;
    }

    ctx.clearRect(0, 0, w, h);

    activeEvents.forEach(evt => {
      const bbox = evt.bbox_norm || [0.3, 0.5, 0.3, 0.2];
      const bx = bbox[0] * w;
      const by = bbox[1] * h;
      const bw = bbox[2] * w;
      const bh = bbox[3] * h;

      const isHigh = evt.severity === 'High';
      const color = isHigh ? '#dc2626' : '#d97706';
      const fillColor = isHigh ? 'rgba(220, 38, 38, 0.15)' : 'rgba(217, 119, 6, 0.15)';

      // Box fill and border
      ctx.fillStyle = fillColor;
      ctx.fillRect(bx, by, bw, bh);
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.strokeRect(bx, by, bw, bh);

      // HUD corner accents
      const clen = Math.min(bw, bh) * 0.25;
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(bx, by + clen); ctx.lineTo(bx, by); ctx.lineTo(bx + clen, by); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(bx + bw - clen, by); ctx.lineTo(bx + bw, by); ctx.lineTo(bx + bw, by + clen); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(bx, by + bh - clen); ctx.lineTo(bx, by + bh); ctx.lineTo(bx + clen, by + bh); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(bx + bw - clen, by + bh); ctx.lineTo(bx + bw, by + bh); ctx.lineTo(bx + bw, by + clen); ctx.stroke();

      // Top Tag
      const labelText = `#${evt.defect_id} ${evt.class_name.toUpperCase()} [${evt.severity.toUpperCase()}] ${(evt.confidence * 100).toFixed(1)}%`;
      ctx.font = 'bold 12px "JetBrains Mono", monospace';
      const tw = ctx.measureText(labelText).width;
      ctx.fillStyle = color;
      ctx.fillRect(bx, Math.max(0, by - 22), tw + 12, 20);
      ctx.fillStyle = '#ffffff';
      ctx.fillText(labelText, bx + 6, Math.max(14, by - 7));
    });
  }

  function triggerPatrolHazard(evt) {
    if (patrolState.detectedEventIds.has(evt.defect_id)) return;
    patrolState.detectedEventIds.add(evt.defect_id);

    // 1. Alert banner in HUD
    if (els.hudHazardAlert && els.hudHazardText) {
      els.hudHazardText.textContent = `${evt.severity.toUpperCase()} RISK ${evt.class_name.toUpperCase()} DETECTED (#${evt.defect_id})`;
      els.hudHazardAlert.style.display = 'flex';
      clearTimeout(patrolState.hazardTimeout);
      patrolState.hazardTimeout = setTimeout(() => {
        if (els.hudHazardAlert) els.hudHazardAlert.style.display = 'none';
      }, 3000);
    }

    // 2. Increment HUD detection count
    if (els.patrolDetectedCount) {
      els.patrolDetectedCount.textContent = patrolState.detectedEventIds.size;
    }

    // 3. Add to sidebar list
    if (els.patrolEmptyState) els.patrolEmptyState.style.display = 'none';
    if (els.patrolEventList) {
      const card = document.createElement('div');
      card.className = `pevent-card event-${evt.severity.toLowerCase()}`;
      card.innerHTML = `
        <div class="pevent-card-top">
          <span class="pevent-badge badge-${evt.severity.toLowerCase()}">${evt.severity} ${evt.class_name.toUpperCase()}</span>
          <span class="pevent-time">${evt.time_sec.toFixed(1)}s</span>
        </div>
        <div class="pevent-street">${evt.street}</div>
        <div class="pevent-coords">GPS: ${evt.gps.latitude.toFixed(4)}° N, ${evt.gps.longitude.toFixed(4)}° E &bull; Conf: ${(evt.confidence * 100).toFixed(1)}%</div>
      `;
      els.patrolEventList.prepend(card);
    }

    // 4. Radar Burst Ping on Google Maps
    if (state.map) {
      const pingMarker = L.circleMarker([evt.gps.latitude, evt.gps.longitude], {
        radius: 26,
        color: '#dc2626',
        weight: 2,
        fillColor: 'rgba(220, 38, 38, 0.4)',
        fillOpacity: 0.8
      }).addTo(state.map);

      setTimeout(() => {
        if (state.map) state.map.removeLayer(pingMarker);
      }, 2400);

      // Permanent marker on markersLayer
      if (state.markersLayer) {
        const pinColor = evt.severity.toLowerCase() === 'high' ? '#dc2626' : '#d97706';
        const permMarker = L.circleMarker([evt.gps.latitude, evt.gps.longitude], {
          radius: evt.severity.toLowerCase() === 'high' ? 9 : 7,
          color: pinColor,
          weight: 2.5,
          fillColor: evt.severity.toLowerCase() === 'high' ? 'rgba(220, 38, 38, 0.5)' : 'rgba(217, 119, 6, 0.4)',
          fillOpacity: 0.85
        });

        const popupContent = `
          <div class="popup-title">#${evt.defect_id} ${evt.class_name.toUpperCase()}</div>
          <div class="popup-meta">
            <span><strong>Zone:</strong> ${evt.zone}</span>
            <span><strong>Locality:</strong> ${evt.area}</span>
            <span><strong>Street:</strong> ${evt.street}</span>
            <span><strong>Severity:</strong> ${evt.severity}</span>
            <span><strong>Status:</strong> reported (Live Patrol Ingested)</span>
          </div>
          <button class="popup-btn" onclick="window.inspectDefect('${evt.defect_id}')">Inspect &amp; Dispatch</button>
        `;
        permMarker.bindPopup(popupContent);
        permMarker.defectData = evt;
        state.markersLayer.addLayer(permMarker);
      }
    }

    // 5. Ingest into active dashboard state & triage list
    const newDefectRecord = {
      id: evt.defect_id,
      defect_id: evt.defect_id,
      class_name: evt.class_name,
      severity: evt.severity,
      confidence: evt.confidence,
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19),
      latitude: evt.gps.latitude,
      longitude: evt.gps.longitude,
      bbox_norm: evt.bbox_norm,
      zone: evt.zone,
      area: evt.area,
      street: evt.street,
      status: 'reported',
      assigned_contractor: 'KMC Rapid Response Unit',
      notes: evt.notes
    };

    // Prepend to state.defects
    state.defects.unshift(newDefectRecord);
    applyFilters();

    // Async sync to backend
    if (state.backendOnline) {
      fetch(`${CONFIG.API_BASE}/api/defects/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify([newDefectRecord])
      }).catch(e => console.info('Live ingest queued locally:', e.message));
    }

    showToast(`🚨 New ${evt.severity} ${evt.class_name} logged at ${evt.street}!`);
  }

  function updatePatrolFrame(currentTimeSec) {
    patrolState.currentTime = currentTimeSec;

    // Update progress slider & time
    if (els.patrolProgress) els.patrolProgress.value = currentTimeSec;
    if (els.patrolTimeDisplay) {
      const curM = Math.floor(currentTimeSec / 60).toString().padStart(2, '0');
      const curS = Math.floor(currentTimeSec % 60).toString().padStart(2, '0');
      const durM = Math.floor(patrolState.duration / 60).toString().padStart(2, '0');
      const durS = Math.floor(patrolState.duration % 60).toString().padStart(2, '0');
      els.patrolTimeDisplay.textContent = `${curM}:${curS} / ${durM}:${durS}`;
    }

    // Vehicle Position on Route
    const pos = getPatrolPosition(currentTimeSec);

    // HUD Text Updates
    if (els.hudLocation) {
      els.hudLocation.textContent = `GPS: ${pos.lat.toFixed(4)}° N, ${pos.lng.toFixed(4)}° E | ${pos.street}`;
    }
    if (els.hudTimestamp) {
      const d = new Date();
      els.hudTimestamp.textContent = d.toTimeString().split(' ')[0];
    }
    if (els.hudStatus) {
      els.hudStatus.textContent = patrolState.isPlaying ? 'SURVEYING [ACTIVE]' : 'PAUSED';
      els.hudStatus.style.color = patrolState.isPlaying ? '#34d399' : '#d97706';
    }

    // Google Maps Vehicle Marker Synchronization
    if (state.map) {
      if (!patrolState.vehicleMarker) {
        patrolState.vehicleMarker = L.marker([pos.lat, pos.lng], {
          icon: L.divIcon({
            className: 'patrol-vehicle-marker',
            html: '<span class="patrol-radar-wave"></span>🚗',
            iconSize: [38, 38],
            iconAnchor: [19, 19]
          }),
          zIndexOffset: 1000
        }).addTo(state.map);
        patrolState.vehicleMarker.bindTooltip('<b>KMC-PATROL-04</b><br>Station Road Survey', { direction: 'top', offset: [0, -18] });
      } else {
        patrolState.vehicleMarker.setLatLng([pos.lat, pos.lng]);
      }
    }

    // Check synchronized defect events
    const events = (patrolState.routeData && patrolState.routeData.events) || DEFAULT_PATROL_ROUTE.events;
    const activeEvents = [];

    events.forEach(evt => {
      const start = evt.time_sec;
      const end = start + (evt.duration || 3.0);
      if (currentTimeSec >= start && currentTimeSec <= end) {
        activeEvents.push(evt);
        triggerPatrolHazard(evt);
      }
    });

    renderPatrolOverlay(activeEvents);
  }

  function patrolLoop() {
    if (!patrolState.isPlaying) return;

    if (els.patrolVideo && !els.patrolVideo.paused) {
      updatePatrolFrame(els.patrolVideo.currentTime);
      if (els.patrolVideo.ended) {
        pausePatrol();
      }
    }

    patrolState.animFrameId = requestAnimationFrame(patrolLoop);
  }

  function startPatrol() {
    if (patrolState.isPlaying) return;
    patrolState.isPlaying = true;

    if (els.btnPatrolPlay) {
      els.btnPatrolPlay.textContent = '▶ Running';
      els.btnPatrolPlay.disabled = true;
    }
    if (els.btnPatrolPause) els.btnPatrolPause.disabled = false;

    if (els.patrolVideo) {
      els.patrolVideo.play().catch(e => {
        console.warn('Auto-play caught:', e);
      });
    }

    patrolLoop();
    showToast('Autonomous Road Patrol active: Telemetry streaming to Google Maps.');
  }

  function pausePatrol() {
    patrolState.isPlaying = false;
    if (els.btnPatrolPlay) {
      els.btnPatrolPlay.textContent = '▶ Resume Patrol';
      els.btnPatrolPlay.disabled = false;
    }
    if (els.btnPatrolPause) els.btnPatrolPause.disabled = true;

    if (els.patrolVideo) {
      els.patrolVideo.pause();
    }
    if (patrolState.animFrameId) {
      cancelAnimationFrame(patrolState.animFrameId);
    }
    if (els.hudStatus) {
      els.hudStatus.textContent = 'PAUSED';
      els.hudStatus.style.color = '#d97706';
    }
  }

  function resetPatrol() {
    pausePatrol();
    if (els.btnPatrolPlay) {
      els.btnPatrolPlay.textContent = '▶ Start Live Patrol';
      els.btnPatrolPlay.disabled = false;
    }
    if (els.patrolVideo) {
      els.patrolVideo.currentTime = 0;
    }
    patrolState.detectedEventIds.clear();
    if (els.patrolDetectedCount) els.patrolDetectedCount.textContent = '0';
    if (els.patrolEventList) {
      els.patrolEventList.innerHTML = '<div class="pevent-empty" id="patrol-empty-state"><p>Start patrol to begin streaming road distress detections onto Google Maps in real time.</p></div>';
    }

    updatePatrolFrame(0);

    // Clear canvas
    if (els.patrolCanvas) {
      const ctx = els.patrolCanvas.getContext('2d');
      if (ctx) ctx.clearRect(0, 0, els.patrolCanvas.width, els.patrolCanvas.height);
    }
  }

  function handleCustomVideoUpload(file) {
    if (!file) return;
    pausePatrol();
    patrolState.isWebcam = false;
    const url = URL.createObjectURL(file);
    if (els.patrolVideo) {
      els.patrolVideo.src = url;
      els.patrolVideo.load();
    }
    showToast(`Loaded custom video: ${file.name}`);
  }

  async function toggleWebcam() {
    if (patrolState.isWebcam) {
      // Stop webcam
      if (patrolState.webcamStream) {
        patrolState.webcamStream.getTracks().forEach(t => t.stop());
        patrolState.webcamStream = null;
      }
      patrolState.isWebcam = false;
      if (els.btnWebcamToggle) els.btnWebcamToggle.textContent = '📷 WebCam';
      if (els.patrolVideo) {
        els.patrolVideo.srcObject = null;
        els.patrolVideo.src = `${CONFIG.API_BASE}/media/dashcam_demo.mp4`;
        els.patrolVideo.load();
      }
      showToast('Switched back to Municipal Dashcam video feed.');
    } else {
      // Start webcam
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
        patrolState.webcamStream = stream;
        patrolState.isWebcam = true;
        if (els.patrolVideo) {
          els.patrolVideo.srcObject = stream;
          els.patrolVideo.play();
        }
        if (els.btnWebcamToggle) els.btnWebcamToggle.textContent = '⏹ Stop Cam';
        startPatrol();
        showToast('Live Camera Feed connected! Streaming live road inference.');
      } catch (err) {
        alert('Could not access camera: ' + err.message);
      }
    }
  }

  /**
   * Event Listeners Setup
   */
  function setupEvents() {
    // Quick Map Filter Buttons
    const mapButtons = [
      { el: els.mapAll, filter: 'all' },
      { el: els.mapPotholes, filter: 'potholes' },
      { el: els.mapCracks, filter: 'cracks' },
      { el: els.mapHigh, filter: 'high' }
    ];

    mapButtons.forEach(item => {
      if (!item.el) return;
      item.el.addEventListener('click', () => {
        mapButtons.forEach(b => b.el.classList.remove('active'));
        item.el.classList.add('active');
        state.activeFilter = item.filter;
        applyFilters();
      });
    });

    // Basemap Switcher Buttons (Google Maps Roadmap, Google Satellite Hybrid, OSM)
    document.querySelectorAll('.basemap-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const bType = btn.dataset.basemap;
        setBasemap(bType);
        const name = bType === 'google-roads' ? 'Google Maps' : bType === 'google-satellite' ? 'Google Satellite Hybrid' : 'OpenStreetMap';
        showToast(`Map switched to ${name}`);
      });
    });

    // Search bar
    els.searchDefects.addEventListener('input', (e) => {
      state.searchQuery = e.target.value;
      applyFilters();
    });

    // Direct Area/Zone Dropdown in Filter Toolbar
    if (els.selectZone) {
      els.selectZone.value = state.currentZone;
      els.selectZone.addEventListener('change', (e) => {
        selectZone(e.target.value);
      });
    }

    // Select Severity & Status
    els.selectSeverity.addEventListener('change', (e) => {
      state.selectedSeverity = e.target.value;
      applyFilters();
    });

    els.selectStatus.addEventListener('change', (e) => {
      state.selectedStatus = e.target.value;
      applyFilters();
    });

    // Top action buttons
    els.btnThemeToggle.addEventListener('click', () => {
      const nextTheme = state.currentTheme === 'light' ? 'dark' : 'light';
      setTheme(nextTheme);
    });

    els.btnSeedData.addEventListener('click', seedLiveDetections);
    els.btnExportReport.addEventListener('click', exportMunicipalReport);

    // Modal controls
    els.modalCloseBtn.addEventListener('click', closeModal);
    els.btnSaveModal.addEventListener('click', saveDefectUpdate);
    els.modal.addEventListener('click', (e) => {
      if (e.target === els.modal) closeModal();
    });

    // Change Area button: Cycles to next Kolhapur area immediately on click!
    if (els.btnSwitchZone) {
      els.btnSwitchZone.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        cycleNextZone();
      });
    }

    // Header Zone Dropdown: Select any area instantly!
    if (els.headerZoneSelect) {
      els.headerZoneSelect.value = state.currentZone;
      els.headerZoneSelect.addEventListener('change', (e) => {
        selectZone(e.target.value);
      });
    }

    // Click on Emblem icon opens full Ward Selection Dialog
    if (els.btnOpenModalIcon) {
      els.btnOpenModalIcon.addEventListener('click', (e) => {
        e.stopPropagation();
        openLoginModal();
      });
    }

    if (els.btnCloseLoginModal) {
      els.btnCloseLoginModal.addEventListener('click', closeLoginModal);
    }

    // Zone Quick Select Cards in Login Modal
    document.querySelectorAll('.zone-select-card').forEach(card => {
      card.addEventListener('click', () => {
        const zone = card.getAttribute('data-zone');
        if (zone) {
          selectZone(zone);
        }
      });
    });

    // Manual Confirm Login
    if (els.btnConfirmLogin) {
      els.btnConfirmLogin.addEventListener('click', () => {
        const selectedZone = els.loginZoneDropdown ? els.loginZoneDropdown.value : 'Central Kolhapur';
        selectZone(selectedZone);
      });
    }

    // Close login modal when clicking backdrop (only if already logged in)
    if (els.zoneLoginModal) {
      els.zoneLoginModal.addEventListener('click', (e) => {
        if (e.target === els.zoneLoginModal && state.isLoggedIn) {
          closeLoginModal();
        }
      });
    }

    // Live Dashcam Patrol HUD Controls
    if (els.btnOpenPatrol) {
      els.btnOpenPatrol.addEventListener('click', openPatrolModal);
    }
    if (els.btnClosePatrol) {
      els.btnClosePatrol.addEventListener('click', closePatrolModal);
    }
    if (els.btnPatrolPlay) {
      els.btnPatrolPlay.addEventListener('click', startPatrol);
    }
    if (els.btnPatrolPause) {
      els.btnPatrolPause.addEventListener('click', pausePatrol);
    }
    if (els.btnPatrolReset) {
      els.btnPatrolReset.addEventListener('click', resetPatrol);
    }
    if (els.patrolProgress) {
      els.patrolProgress.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        if (els.patrolVideo) els.patrolVideo.currentTime = val;
        updatePatrolFrame(val);
      });
    }
    if (els.inputUploadVideo) {
      els.inputUploadVideo.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) handleCustomVideoUpload(e.target.files[0]);
      });
    }
    if (els.btnWebcamToggle) {
      els.btnWebcamToggle.addEventListener('click', toggleWebcam);
    }
    if (els.btnSyncMapFocus) {
      els.btnSyncMapFocus.addEventListener('click', () => {
        if (patrolState.vehicleMarker && state.map) {
          state.map.panTo(patrolState.vehicleMarker.getLatLng(), { animate: true });
          closePatrolModal();
          showToast('Focused Google Map on active patrol unit.');
        }
      });
    }
    if (els.patrolModal) {
      els.patrolModal.addEventListener('click', (e) => {
        if (e.target === els.patrolModal) closePatrolModal();
      });
    }

    // Mobile Camera Pairing Controls
    async function openMobileModal() {
      if (!els.mobilePairModal) return;
      els.mobilePairModal.style.display = 'flex';
      try {
        const res = await fetch('/api/system/network_info');
        const data = await res.json();
        if (els.mobileHudUrlText) {
          els.mobileHudUrlText.textContent = data.mobile_hud_url;
        }
        if (els.mobileQrImg) {
          els.mobileQrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&margin=4&data=${encodeURIComponent(data.mobile_hud_url)}`;
        }
      } catch (e) {
        const fallbackUrl = `${window.location.protocol}//${window.location.hostname}:8000/mobile.html`;
        if (els.mobileHudUrlText) els.mobileHudUrlText.textContent = fallbackUrl;
        if (els.mobileQrImg) {
          els.mobileQrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&margin=4&data=${encodeURIComponent(fallbackUrl)}`;
        }
      }
    }

    function closeMobileModal() {
      if (els.mobilePairModal) els.mobilePairModal.style.display = 'none';
    }

    if (els.btnOpenMobile) {
      els.btnOpenMobile.addEventListener('click', openMobileModal);
    }
    if (els.btnCloseMobileModal) {
      els.btnCloseMobileModal.addEventListener('click', closeMobileModal);
    }
    if (els.mobilePairModal) {
      els.mobilePairModal.addEventListener('click', (e) => {
        if (e.target === els.mobilePairModal) closeMobileModal();
      });
    }
    if (els.btnCopyMobileUrl) {
      els.btnCopyMobileUrl.addEventListener('click', () => {
        const url = els.mobileHudUrlText ? els.mobileHudUrlText.textContent.trim() : '';
        if (url && navigator.clipboard) {
          navigator.clipboard.writeText(url).then(() => {
            showToast('Mobile URL copied to clipboard!', 'success');
          });
        }
      });
    }

    // Operational Zone Map Legend click delegation
    document.querySelectorAll('#map-legend .legend-item[data-zone]').forEach(item => {
      item.addEventListener('click', () => {
        const zid = item.getAttribute('data-zone');
        const zoneNameMap = {
          'central_kolhapur': 'Central Kolhapur',
          'north_kolhapur': 'North Kolhapur',
          'south_kolhapur': 'South Kolhapur',
          'east_kolhapur': 'East Kolhapur',
          'west_kolhapur': 'West Kolhapur'
        };
        const targetZone = zoneNameMap[zid] || 'Central Kolhapur';
        selectZone(targetZone);
      });
    });

    // Expose inspect function globally for Leaflet popup call
    window.inspectDefect = function (id) {
      const defect = state.defects.find(d => String(d.id || d.defect_id) === String(id));
      if (defect) openInspectionModal(defect);
    };
  }

  // Application Entry Point
  function initApp() {
    setTheme(state.currentTheme);
    initMap();
    setupEvents();
    
    // Set initial zone presentation in badge & dropdowns
    const initialZone = KOLHAPUR_ZONES[state.currentZone] || KOLHAPUR_ZONES['all'];
    if (els.officerTitleDisplay) els.officerTitleDisplay.textContent = initialZone.title;
    if (els.officerAreasDisplay) els.officerAreasDisplay.textContent = initialZone.areas;
    if (els.headerZoneSelect) els.headerZoneSelect.value = state.currentZone;
    if (els.selectZone) els.selectZone.value = state.currentZone;
    if (els.loginZoneDropdown) els.loginZoneDropdown.value = state.currentZone;

    loadData();

    // If first visit, show Kolhapur Zone selection modal
    if (!state.isLoggedIn) {
      openLoginModal();
    }
  }

  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', initApp);
  } else {
    initApp();
  }

})();
