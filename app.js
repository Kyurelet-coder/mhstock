/* ==========================================================================
   MONSTER HIGH STOCK & COLLECTION MANAGER PRO - MOBILE / ANDROID PWA LOGIC
   ========================================================================== */

const COLLECTIONS = [
  "Creeproduction", "Signature (G1)", "Signature (G3)", "Skullector",
  "13 Wishes", "Boo York, Boo York", "Budget Dolls", "Dead Tired",
  "Dot Dead Gorgeous", "Fang Vote", "Freak Du Chic", "Freaky Fusion",
  "Great Scarrier Reef", "Haunted", "I <3 Fashion", "Monster Fest",
  "New Scaremester", "Picture Day", "Roller Maze", "Scaris: City of Frights",
  "Sweet 1600", "Other"
];

// Initial Seed Inventory Data
const INITIAL_SEED_DOLLS = [
  {
    id: 1,
    name: "Rochelle creeproduction (Coleção)",
    character: "Rochelle",
    line: "Creeproduction",
    condition: "NIB",
    status: "personal",
    purchasePrice: 35.57,
    sellingPrice: 0.00,
    soldPrice: null,
    batchId: "#00001-Rochelle creeproduction",
    notes: "Coleção Própria",
    hairstyleDifficulty: "Simples 🟢",
    photoUrl: null
  },
  {
    id: 2,
    name: "Rochelle creeproduction (Revenda #1)",
    character: "Rochelle",
    line: "Creeproduction",
    condition: "NIB",
    status: "in_stock",
    purchasePrice: 35.57,
    sellingPrice: 53.35,
    soldPrice: null,
    batchId: "#00001-Rochelle creeproduction",
    notes: "Revenda para amortizar lote",
    hairstyleDifficulty: "Simples 🟢",
    photoUrl: null
  },
  {
    id: 3,
    name: "Rochelle creeproduction (Revenda #2)",
    character: "Rochelle",
    line: "Creeproduction",
    condition: "NIB",
    status: "in_stock",
    purchasePrice: 35.57,
    sellingPrice: 53.35,
    soldPrice: null,
    batchId: "#00001-Rochelle creeproduction",
    notes: "Revenda para amortizar lote",
    hairstyleDifficulty: "Simples 🟢",
    photoUrl: null
  },
  {
    id: 4,
    name: "Honey Swamp",
    character: "Honey Swamp",
    line: "Signature (G1)",
    condition: "To be restored",
    status: "in_stock",
    purchasePrice: 18.15,
    sellingPrice: 45.00,
    soldPrice: null,
    batchId: null,
    notes: "Para restauro individual",
    hairstyleDifficulty: "Difícil 🔴",
    photoUrl: null
  },
  {
    id: 5,
    name: "C.A Cupid",
    character: "C.A Cupid",
    line: "Other",
    condition: "Good",
    status: "sold",
    purchasePrice: 16.05,
    sellingPrice: 45.00,
    soldPrice: 45.20,
    batchId: null,
    notes: "Vendido",
    hairstyleDifficulty: "Médio 🟡",
    photoUrl: null
  }
];

const INITIAL_SEED_WISHLIST = [
  { id: 1, name: "Elissabat (Frights Camera Action)", maxPrice: 45.00, priority: "Alta 🔥" },
  { id: 2, name: "C.A. Cupid (Sweet 1600)", maxPrice: 35.00, priority: "Média ⭐" }
];

class MHStockApp {
  constructor() {
    this.dolls = [];
    this.wishlist = [];
    this.currentViewMode = 'grid';
    this.currentPhotoBase64 = null;
    this.selectedCardDollId = null;
    this.init();
  }

  init() {
    this.loadState();
    this.populateLineDropdowns();
    this.populateSimBatchDropdown();
    this.bindEvents();
    this.render();
    this.updateSimulator();
  }

  loadState() {
    const savedDolls = localStorage.getItem('mh_stock_data_v16');
    if (savedDolls) {
      try { 
        this.dolls = JSON.parse(savedDolls);
      } catch (e) {
        this.dolls = INITIAL_SEED_DOLLS;
      }
    } else {
      this.dolls = INITIAL_SEED_DOLLS;
      this.saveState();
    }

    const savedWish = localStorage.getItem('mh_wishlist_data_v1');
    if (savedWish) {
      try { this.wishlist = JSON.parse(savedWish); } catch (e) { this.wishlist = INITIAL_SEED_WISHLIST; }
    } else {
      this.wishlist = INITIAL_SEED_WISHLIST;
    }
  }

  saveState() {
    try {
      localStorage.setItem('mh_stock_data_v16', JSON.stringify(this.dolls));
      localStorage.setItem('mh_wishlist_data_v1', JSON.stringify(this.wishlist));
    } catch (e) {
      console.warn("localStorage quota or write warning:", e);
    }
    this.populateSimBatchDropdown();
    this.render();
  }

  getNextBatchId(lotName) {
    let maxNum = 0;
    this.dolls.forEach(d => {
      if (d.batchId) {
        const match = d.batchId.match(/^#(\d{5})/);
        if (match) {
          const num = parseInt(match[1], 10);
          if (num > maxNum) maxNum = num;
        }
      }
    });

    const nextNumStr = String(maxNum + 1).padStart(5, '0');
    const cleanName = (lotName || 'Lote').trim();
    return `#${nextNumStr}-${cleanName}`;
  }

  populateLineDropdowns() {
    const colFilter = document.getElementById('filter-collection');
    const formLine = document.getElementById('form-line');

    COLLECTIONS.forEach(col => {
      const opt1 = document.createElement('option');
      opt1.value = col;
      opt1.textContent = col;
      colFilter.appendChild(opt1);

      const opt2 = document.createElement('option');
      opt2.value = col;
      opt2.textContent = col;
      formLine.appendChild(opt2);
    });
  }

  populateSimBatchDropdown() {
    const select = document.getElementById('sim-batch-select');
    if (!select) return;

    select.innerHTML = '<option value="CUSTOM">⚡ Personalizado (Digitar Dados)</option>';

    const batches = [...new Set(this.dolls.map(d => d.batchId).filter(Boolean))];
    batches.forEach(bId => {
      const opt = document.createElement('option');
      opt.value = bId;
      opt.textContent = `📦 ${bId}`;
      select.appendChild(opt);
    });
  }

  bindEvents() {
    // Search and filters
    document.getElementById('search-input').addEventListener('input', () => this.render());
    document.getElementById('filter-status').addEventListener('change', () => this.render());
    document.getElementById('filter-collection').addEventListener('change', () => this.render());

    // View toggle
    document.getElementById('view-grid-btn').addEventListener('click', () => this.setViewMode('grid'));
    document.getElementById('view-table-btn').addEventListener('click', () => this.setViewMode('table'));

    // Main Section Tabs
    document.getElementById('tab-btn-stock').addEventListener('click', () => this.switchTab('stock'));
    document.getElementById('tab-btn-shelf').addEventListener('click', () => this.switchTab('shelf'));
    document.getElementById('tab-btn-analytics').addEventListener('click', () => this.switchTab('analytics'));
    document.getElementById('tab-btn-wishlist').addEventListener('click', () => this.switchTab('wishlist'));
    document.getElementById('tab-btn-simulator').addEventListener('click', () => this.switchTab('simulator'));

    // Modals open/close
    document.getElementById('btn-add-header').addEventListener('click', () => this.openDollModal());
    document.getElementById('close-doll-modal').addEventListener('click', () => this.closeDollModal());
    
    document.getElementById('btn-batch-header').addEventListener('click', () => this.openBatchModal());
    document.getElementById('close-batch-modal').addEventListener('click', () => this.closeBatchModal());
    document.getElementById('close-sell-modal').addEventListener('click', () => this.closeSellModal());
    document.getElementById('close-wishlist-modal').addEventListener('click', () => this.closeWishlistModal());
    document.getElementById('close-card-modal').addEventListener('click', () => this.closeCardModal());

    document.getElementById('btn-add-wishlist').addEventListener('click', () => this.openWishlistModal());
    document.getElementById('btn-download-card').addEventListener('click', () => this.downloadTradingCard());
    document.getElementById('btn-export-csv').addEventListener('click', () => this.exportCSV());

    // Photo Input change with auto-canvas compression
    document.getElementById('form-photo-input').addEventListener('change', (e) => this.handlePhotoUpload(e));

    // Dynamic visibility of selling price fields based on selected status
    document.getElementById('form-status').addEventListener('change', () => this.onFormStatusChange());

    // Form submits
    document.getElementById('doll-form').addEventListener('submit', (e) => this.handleDollSubmit(e));
    document.getElementById('batch-form').addEventListener('submit', (e) => this.handleBatchSubmit(e));
    document.getElementById('sell-form').addEventListener('submit', (e) => this.handleSellSubmit(e));
    document.getElementById('wishlist-form').addEventListener('submit', (e) => this.handleWishlistSubmit(e));

    // Batch Creator dynamic calculation inputs
    document.getElementById('batch-total-cost').addEventListener('input', () => this.updateBatchPreview());
    document.getElementById('batch-shipping').addEventListener('input', () => this.updateBatchPreview());
    document.getElementById('batch-total-units').addEventListener('input', () => this.updateBatchPreview());
    document.getElementById('batch-personal-units').addEventListener('input', () => this.updateBatchPreview());
    document.getElementById('batch-est-sell-price').addEventListener('input', () => this.updateBatchPreview());

    // Sell modal fee preview
    document.getElementById('sell-platform').addEventListener('change', () => this.updateSellFeePreview());
    document.getElementById('sell-price-input').addEventListener('input', () => this.updateSellFeePreview());

    // Interactive Slider Simulator & Dynamic Batch Select
    const slider = document.getElementById('resale-slider');
    slider.addEventListener('input', () => this.updateSimulator());

    document.getElementById('sim-batch-select').addEventListener('change', (e) => this.onSimBatchSelect(e.target.value));
    document.getElementById('sim-input-cost').addEventListener('input', () => this.updateSimulator());
    document.getElementById('sim-input-tot-units').addEventListener('input', () => this.updateSimulator());
    document.getElementById('sim-input-pers-units').addEventListener('input', () => this.updateSimulator());

    // Android Bottom Navigation
    document.getElementById('nav-stock').addEventListener('click', () => this.switchTab('stock', 'nav-stock'));
    document.getElementById('nav-shelf').addEventListener('click', () => this.switchTab('shelf', 'nav-shelf'));
    document.getElementById('nav-analytics').addEventListener('click', () => this.switchTab('analytics', 'nav-analytics'));
    document.getElementById('nav-wishlist').addEventListener('click', () => this.switchTab('wishlist', 'nav-wishlist'));
    document.getElementById('nav-add').addEventListener('click', () => this.openDollModal());
  }

  // --- AUTOMATIC CANVAS COMPRESSION FOR ULTRA-FAST BASE64 STORAGE ---
  handlePhotoUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const img = new Image();
    const url = URL.createObjectURL(file);

    img.onload = () => {
      const canvas = document.createElement('canvas');
      const maxDim = 600;
      let width = img.width;
      let height = img.height;

      if (width > height) {
        if (width > maxDim) {
          height = Math.round((height * maxDim) / width);
          width = maxDim;
        }
      } else {
        if (height > maxDim) {
          width = Math.round((width * maxDim) / height);
          height = maxDim;
        }
      }

      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, width, height);

      // Compress to lightweight 75% JPEG (~40KB)
      this.currentPhotoBase64 = canvas.toDataURL('image/jpeg', 0.75);

      const previewCont = document.getElementById('photo-preview-container');
      const previewImg = document.getElementById('photo-preview-img');
      previewImg.src = this.currentPhotoBase64;
      previewCont.style.display = 'block';

      URL.revokeObjectURL(url);
    };

    img.src = url;
  }

  onFormStatusChange() {
    const status = document.getElementById('form-status').value;
    const sellGroup = document.getElementById('form-sell-group');
    const soldGroup = document.getElementById('form-sold-group');

    if (status === 'personal') {
      sellGroup.style.display = 'none';
      soldGroup.style.display = 'none';
      document.getElementById('form-sell').value = '0.00';
      document.getElementById('form-sold').value = '';
    } else if (status === 'in_stock') {
      sellGroup.style.display = 'block';
      soldGroup.style.display = 'none';
      document.getElementById('form-sold').value = '';
    } else if (status === 'sold') {
      sellGroup.style.display = 'block';
      soldGroup.style.display = 'block';
    }
  }

  onSimBatchSelect(bId) {
    if (bId === 'CUSTOM') return;

    const batchDolls = this.dolls.filter(d => d.batchId === bId);
    if (batchDolls.length === 0) return;

    const totCost = batchDolls.reduce((sum, d) => sum + (d.purchasePrice || 0), 0);
    const totUnits = batchDolls.length;
    const persUnits = batchDolls.filter(d => d.status === 'personal').length;
    const resaleUnits = totUnits - persUnits;

    document.getElementById('sim-input-cost').value = totCost.toFixed(2);
    document.getElementById('sim-input-tot-units').value = totUnits;
    document.getElementById('sim-input-pers-units').value = persUnits;

    if (resaleUnits > 0) {
      const recPrice = Math.round(totCost / resaleUnits);
      document.getElementById('resale-slider').value = recPrice;
    }

    this.updateSimulator();
  }

  switchTab(tabName, navId = null) {
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    if (navId) document.getElementById(navId).classList.add('active');

    document.getElementById('section-stock-view').style.display = tabName === 'stock' ? 'block' : 'none';
    document.getElementById('section-shelf-view').style.display = tabName === 'shelf' ? 'block' : 'none';
    document.getElementById('section-analytics-view').style.display = tabName === 'analytics' ? 'block' : 'none';
    document.getElementById('section-wishlist-view').style.display = tabName === 'wishlist' ? 'block' : 'none';
    document.getElementById('section-simulator-view').style.display = tabName === 'simulator' ? 'block' : 'none';

    if (tabName === 'shelf') this.renderVirtualShelf();
    if (tabName === 'analytics') this.renderAnalytics();
    if (tabName === 'wishlist') this.renderWishlist();
  }

  setViewMode(mode) {
    this.currentViewMode = mode;
    document.getElementById('view-grid-btn').classList.toggle('active', mode === 'grid');
    document.getElementById('view-table-btn').classList.toggle('active', mode === 'table');
    document.getElementById('dolls-grid-container').style.display = mode === 'grid' ? 'block' : 'none';
    document.getElementById('dolls-table-container').style.display = mode === 'table' ? 'block' : 'none';
  }

  getBatchAmortizationMap() {
    const batchMap = {};
    this.dolls.forEach(d => {
      if (!d.batchId) return;
      if (!batchMap[d.batchId]) {
        batchMap[d.batchId] = { totalCost: 0, soldRevenue: 0, personalCost: 0, personalCount: 0, resaleCount: 0 };
      }
      const b = batchMap[d.batchId];
      b.totalCost += (d.purchasePrice || 0);

      if (d.status === 'sold') {
        b.soldRevenue += (d.soldPrice || d.sellingPrice || 0);
      } else if (d.status === 'personal') {
        b.personalCost += (d.purchasePrice || 0);
        b.personalCount++;
      } else {
        b.resaleCount++;
      }
    });
    return batchMap;
  }

  updateSimulator() {
    const slider = document.getElementById('resale-slider');
    const priceVal = parseFloat(slider.value) || 0;
    document.getElementById('slider-price-val').textContent = `€${priceVal.toFixed(2)}`;

    const totCost = parseFloat(document.getElementById('sim-input-cost').value) || 0;
    const totUnits = parseInt(document.getElementById('sim-input-tot-units').value) || 1;
    const persUnits = parseInt(document.getElementById('sim-input-pers-units').value) || 0;
    const resaleUnits = Math.max(1, totUnits - persUnits);

    const expRev = priceVal * resaleUnits;

    document.getElementById('sim-tot-cost').textContent = `€${totCost.toFixed(2)}`;
    document.getElementById('sim-rev-val').textContent = `€${expRev.toFixed(2)}`;
    document.getElementById('sim-units-sub').textContent = `${totUnits} unidades (${persUnits} Coleção + ${resaleUnits} Revenda)`;
    document.getElementById('sim-resale-sub').textContent = `${resaleUnits}x €${priceVal.toFixed(2)}`;

    const personalInitialCost = (totCost / totUnits) * persUnits;
    const effectiveCost = Math.max(0, personalInitialCost - Math.max(0, expRev - (totCost - personalInitialCost)));
    
    const effCostEl = document.getElementById('sim-eff-cost');
    const statusBadge = document.getElementById('sim-status-badge');

    effCostEl.textContent = `€${effectiveCost.toFixed(2)}`;

    if (effectiveCost === 0) {
      effCostEl.className = 'slider-kpi-val amortized-zero';
      statusBadge.textContent = `✨ AMORTIZADA A 100% (0.00€)! 🎉`;
      statusBadge.style.color = 'var(--pink-neon)';
    } else {
      effCostEl.className = 'slider-kpi-val';
      const pct = personalInitialCost > 0 ? Math.round(((personalInitialCost - effectiveCost) / personalInitialCost) * 100) : 0;
      statusBadge.textContent = `${pct}% Amortizado (Faltam €${effectiveCost.toFixed(2)})`;
      statusBadge.style.color = 'var(--cyan-mint)';
    }
  }

  render() {
    const search = document.getElementById('search-input').value.toLowerCase().trim();
    const filterSt = document.getElementById('filter-status').value;
    const filterCol = document.getElementById('filter-collection').value;

    const batchMap = this.getBatchAmortizationMap();

    const filtered = this.dolls.filter(d => {
      const matchSearch = !search ||
        (d.name && d.name.toLowerCase().includes(search)) ||
        (d.character && d.character.toLowerCase().includes(search)) ||
        (d.batchId && d.batchId.toLowerCase().includes(search));

      const matchStatus = filterSt === 'ALL' || d.status === filterSt;
      const matchCol = filterCol === 'ALL' || d.line === filterCol;

      return matchSearch && matchStatus && matchCol;
    });

    this.renderKPIs(batchMap);
    this.renderGrid(filtered, batchMap);
    this.renderTable(filtered, batchMap);
    this.renderVirtualShelf();
  }

  renderKPIs(batchMap) {
    const personal = this.dolls.filter(d => d.status === 'personal');
    const stock = this.dolls.filter(d => d.status === 'in_stock');
    const sold = this.dolls.filter(d => d.status === 'sold');

    // Total Spent across all purchases
    const totalSpent = this.dolls.reduce((sum, d) => sum + (d.purchasePrice || 0), 0);

    // Total Received across all sales
    const totalReceived = sold.reduce((sum, d) => sum + (d.soldPrice || d.sellingPrice || 0), 0);

    // Net Profit from sold items
    const totalProfit = sold.reduce((sum, d) => sum + ((d.soldPrice || d.sellingPrice || 0) - (d.purchasePrice || 0)), 0);

    let totalPersonalEffectiveCost = 0;
    personal.forEach(d => {
      let eff = d.purchasePrice || 0;
      if (d.batchId && batchMap[d.batchId]) {
        eff = Math.max(0, eff - batchMap[d.batchId].soldRevenue);
      }
      totalPersonalEffectiveCost += eff;
    });

    const stockInvestment = stock.reduce((sum, d) => sum + (d.purchasePrice || 0), 0);

    const totalPersonalCostRaw = personal.reduce((sum, d) => sum + (d.purchasePrice || 0), 0);
    let globalAmortPct = 0;
    if (totalPersonalCostRaw > 0) {
      const offset = Math.max(0, totalPersonalCostRaw - totalPersonalEffectiveCost);
      globalAmortPct = Math.round((offset / totalPersonalCostRaw) * 100);
    }

    document.getElementById('kpi-spent-total').textContent = `€${totalSpent.toFixed(2)}`;
    document.getElementById('kpi-spent-sub').textContent = `${this.dolls.length} itens comprados`;

    document.getElementById('kpi-received-total').textContent = `€${totalReceived.toFixed(2)}`;
    document.getElementById('kpi-received-sub').textContent = `${sold.length} venda(s) realizada(s)`;

    document.getElementById('kpi-personal-count').textContent = `${personal.length} itens`;
    document.getElementById('kpi-personal-sub').textContent = `Custo Ef.: €${totalPersonalEffectiveCost.toFixed(2)}`;

    document.getElementById('kpi-stock-count').textContent = `${stock.length} itens`;
    document.getElementById('kpi-stock-sub').textContent = `Investimento: €${stockInvestment.toFixed(2)}`;

    document.getElementById('kpi-profit-total').textContent = `${totalProfit >= 0 ? '+' : ''}€${totalProfit.toFixed(2)}`;
    document.getElementById('kpi-profit-sub').textContent = `${sold.length} itens vendidos`;

    document.getElementById('kpi-amort-pct').textContent = `${globalAmortPct}%`;
  }

  renderGrid(items, batchMap) {
    const container = document.getElementById('dolls-grid-container');
    container.innerHTML = '';

    if (items.length === 0) {
      container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 40px;">Nenhuma boneca encontrada com os filtros selecionados.</div>`;
      return;
    }

    const filterSt = document.getElementById('filter-status').value;

    const personalItems = items.filter(d => d.status === 'personal');
    const stockLotItems = items.filter(d => d.status === 'in_stock' && d.batchId);
    const stockIndividualItems = items.filter(d => d.status === 'in_stock' && !d.batchId);
    const soldItems = items.filter(d => d.status === 'sold');

    // If user explicitly picked "Coleção Própria" in the dropdown filter:
    if (filterSt === 'personal') {
      if (personalItems.length > 0) {
        const persHeader = document.createElement('div');
        persHeader.className = 'main-section-header pink-accent';
        persHeader.innerHTML = `<h2>🟣 COLEÇÃO PRÓPRIA (${personalItems.length} bonecas)</h2>`;
        container.appendChild(persHeader);

        const persGrid = document.createElement('div');
        persGrid.className = 'doll-grid';
        personalItems.forEach(d => persGrid.appendChild(this._createDollCardElement(d, batchMap)));
        container.appendChild(persGrid);
      } else {
        container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 40px;">Nenhuma boneca na Coleção Própria. Consulte a aba "Estante Virtual"!</div>`;
      }
      return;
    }

    // 1. SECTION: 📦 LOTES (Only Resale dolls in batches)
    if (stockLotItems.length > 0) {
      const lotHeader = document.createElement('div');
      lotHeader.className = 'main-section-header pink-accent';
      lotHeader.innerHTML = `<h2>📦 LOTES (${stockLotItems.length} unidades em stock)</h2>`;
      container.appendChild(lotHeader);

      const groupedBatches = {};
      stockLotItems.forEach(d => {
        if (!groupedBatches[d.batchId]) groupedBatches[d.batchId] = [];
        groupedBatches[d.batchId].push(d);
      });

      Object.keys(groupedBatches).forEach(bId => {
        const bDolls = groupedBatches[bId];
        const bInfo = batchMap[bId] || { totalCost: 0, soldRevenue: 0 };
        const stockCount = bDolls.length;

        let effCost = 0;
        const allBatchPersonalDolls = this.dolls.filter(d => d.batchId === bId && d.status === 'personal');
        allBatchPersonalDolls.forEach(d => {
          effCost += Math.max(0, (d.purchasePrice || 0) - bInfo.soldRevenue);
        });

        const batchCard = document.createElement('div');
        batchCard.className = 'batch-section-card';
        batchCard.innerHTML = `
          <div class="batch-section-header">
            <div class="batch-section-title">📦 Lote: ${bId}</div>
            <div class="batch-section-metrics">
              <span class="batch-metric-tag">💰 Custo Total Lote: €${bInfo.totalCost.toFixed(2)}</span>
              <span class="batch-metric-tag">🟢 ${stockCount} Revenda em Stock</span>
              <span class="batch-metric-tag" style="color: var(--pink-neon); font-weight: 700;">
                ${effCost === 0 ? '✨ COLEÇÃO AMORTIZADA A 0.00€!' : 'Custo Ef. Coleção: €' + effCost.toFixed(2)}
              </span>
            </div>
          </div>
          <div class="doll-grid" id="grid-batch-${bId.replace(/[^a-zA-Z0-9]/g,'')}"></div>
        `;
        container.appendChild(batchCard);

        const subGrid = batchCard.querySelector('.doll-grid');
        bDolls.forEach(d => subGrid.appendChild(this._createDollCardElement(d, batchMap)));
      });
    }

    // 2. SECTION: 🎴 BONECAS INDIVIDUAIS (Only Resale individual dolls)
    if (stockIndividualItems.length > 0) {
      const indHeader = document.createElement('div');
      indHeader.className = 'main-section-header cyan-accent';
      indHeader.innerHTML = `<h2>🎴 BONECAS INDIVIDUAIS (${stockIndividualItems.length} unidades em stock)</h2>`;
      container.appendChild(indHeader);

      const indGrid = document.createElement('div');
      indGrid.className = 'doll-grid';
      stockIndividualItems.forEach(d => indGrid.appendChild(this._createDollCardElement(d, batchMap)));
      container.appendChild(indGrid);
    }

    // 3. SECTION: 🔵 BONECAS VENDIDAS (At the very bottom)
    if (soldItems.length > 0) {
      const soldHeader = document.createElement('div');
      soldHeader.className = 'main-section-header gold-accent';
      soldHeader.innerHTML = `<h2>🔵 BONECAS VENDIDAS (${soldItems.length} vendidas)</h2>`;
      container.appendChild(soldHeader);

      const soldGrid = document.createElement('div');
      soldGrid.className = 'doll-grid';
      soldItems.forEach(d => soldGrid.appendChild(this._createDollCardElement(d, batchMap)));
      container.appendChild(soldGrid);
    }
  }

  _createDollCardElement(d, batchMap) {
    const card = document.createElement('div');
    card.className = `doll-card ${d.status === 'personal' ? 'personal-card' : ''}`;

    let badgeHtml = '';
    let effCostStr = '-';

    if (d.status === 'personal') {
      badgeHtml = `<span class="badge badge-personal">🟣 Coleção</span>`;
      let effCost = d.purchasePrice || 0;
      if (d.batchId && batchMap[d.batchId]) {
        effCost = Math.max(0, effCost - batchMap[d.batchId].soldRevenue);
      }
      effCostStr = effCost === 0 ? `✨ 0.00€` : `€${effCost.toFixed(2)}`;
    } else if (d.status === 'sold') {
      badgeHtml = `<span class="badge badge-sold">🔵 Vendido</span>`;
    } else {
      badgeHtml = `<span class="badge badge-stock">🟢 Em Stock</span>`;
    }

    const photoHtml = d.photoUrl ? `<img src="${d.photoUrl}" class="doll-photo-thumb" alt="${d.name}">` : '';
    const hairstyleTag = d.hairstyleDifficulty ? `<div style="font-size: 0.72rem; color: var(--purple-electric); margin-top: 4px;">💇‍♀️ Penteado: ${d.hairstyleDifficulty}</div>` : '';

    let metricsHtml = '';
    if (d.status === 'sold') {
      const profit = (d.soldPrice || 0) - (d.purchasePrice || 0);
      const estVenda = d.sellingPrice ? `€${d.sellingPrice.toFixed(2)}` : '-';
      metricsHtml = `
        <div class="metric-item">
          <span class="metric-label">Custo Compra</span>
          <span class="metric-val">€${(d.purchasePrice || 0).toFixed(2)}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">Est. Venda</span>
          <span class="metric-val" style="color: var(--cyan-mint);">${estVenda}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">Preço Vendido</span>
          <span class="metric-val highlight-profit">€${(d.soldPrice || 0).toFixed(2)}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">Lucro Diferencial</span>
          <span class="metric-val" style="color: var(--gold-accent); font-weight: 800;">${profit >= 0 ? '+' : ''}€${profit.toFixed(2)}</span>
        </div>
      `;
    } else if (d.status === 'in_stock') {
      const estProfit = (d.sellingPrice || 0) - (d.purchasePrice || 0);
      metricsHtml = `
        <div class="metric-item">
          <span class="metric-label">Custo Compra</span>
          <span class="metric-val">€${(d.purchasePrice || 0).toFixed(2)}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">Est. Venda</span>
          <span class="metric-val">€${(d.sellingPrice || 0).toFixed(2)}</span>
        </div>
        <div class="metric-item" style="grid-column: span 2; margin-top: 4px;">
          <span class="metric-label">Estimativa de Lucro</span>
          <span class="metric-val" style="color: var(--cyan-mint); font-weight: 800; font-size: 0.95rem;">${estProfit >= 0 ? '+' : ''}€${estProfit.toFixed(2)}</span>
        </div>
      `;
    } else {
      metricsHtml = `
        <div class="metric-item">
          <span class="metric-label">Custo Compra</span>
          <span class="metric-val">€${(d.purchasePrice || 0).toFixed(2)}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">Custo Efetivo</span>
          <span class="metric-val highlight-eff">${effCostStr}</span>
        </div>
      `;
    }

    card.innerHTML = `
      <div>
        ${photoHtml}
        <div class="doll-header">
          <div>
            <div class="doll-char">${d.character || 'Monster High'}</div>
            <div class="doll-name">${d.name}</div>
          </div>
          ${badgeHtml}
        </div>

        <div class="doll-line">${d.line || 'Outra Linha'} • Condição: ${d.condition || 'NIB'}</div>
        ${hairstyleTag}

        <div class="doll-metrics">
          ${metricsHtml}
        </div>

        ${d.batchId ? `<div class="batch-tag">📦 Lote: ${d.batchId}</div>` : ''}
      </div>

      <div class="card-actions">
        ${d.status === 'in_stock' ? `<button class="btn btn-cyan" onclick="app.openSellModal(${d.id})">💰 Vender</button>` : ''}
        ${d.status === 'in_stock' ? `<button class="btn btn-outline btn-copy-ad" onclick="app.copyVintedAd(${d.id})">📋 Copiar Anúncio</button>` : ''}
        ${d.status === 'personal' ? `<button class="btn btn-cyan" onclick="app.moveToResale(${d.id})">🟢 Pôr à Venda</button>` : ''}
        ${d.status === 'personal' ? `<button class="btn btn-purple" onclick="app.generateTradingCard(${d.id})">🖼️ Trading Card</button>` : ''}
        ${d.status === 'in_stock' ? `<button class="btn btn-purple" onclick="app.moveToPersonal(${d.id})">🟣 Coleção</button>` : ''}
        <button class="btn btn-outline" onclick="app.openDollModal(${d.id})">✏️ Editar</button>
        <button class="btn btn-outline" style="color: var(--red-accent);" onclick="app.deleteDoll(${d.id})">🗑️</button>
      </div>
    `;

    return card;
  }

  renderTable(items, batchMap) {
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = '';

    items.forEach(d => {
      const tr = document.createElement('tr');
      let eff = '-';
      if (d.status === 'personal') {
        let effVal = d.purchasePrice || 0;
        if (d.batchId && batchMap[d.batchId]) {
          effVal = Math.max(0, effVal - batchMap[d.batchId].soldRevenue);
        }
        eff = `€${effVal.toFixed(2)}`;
      }

      const imgHtml = d.photoUrl ? `<img src="${d.photoUrl}" style="width: 32px; height: 32px; border-radius: 4px; object-fit: cover;">` : '🧟‍♀️';

      tr.innerHTML = `
        <td>${d.id}</td>
        <td>${imgHtml}</td>
        <td><strong>${d.name}</strong></td>
        <td>${d.character || '-'}</td>
        <td>${d.line || '-'}</td>
        <td>${d.condition || '-'}</td>
        <td>${d.status === 'personal' ? '🟣 Coleção' : (d.status === 'sold' ? '🔵 Vendido' : '🟢 Stock')}</td>
        <td>${d.hairstyleDifficulty || '-'}</td>
        <td>€${(d.purchasePrice || 0).toFixed(2)}</td>
        <td>${d.sellingPrice ? '€' + d.sellingPrice.toFixed(2) : '-'}</td>
        <td>${d.soldPrice ? '€' + d.soldPrice.toFixed(2) : '-'}</td>
        <td>${eff}</td>
        <td>
          <button class="btn btn-outline" style="padding: 4px 8px;" onclick="app.openDollModal(${d.id})">✏️</button>
          <button class="btn btn-outline" style="padding: 4px 8px; color: var(--red-accent);" onclick="app.deleteDoll(${d.id})">🗑️</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  renderAnalytics() {
    const charProfitMap = {};
    this.dolls.forEach(d => {
      const char = d.character || 'Monster High';
      if (!charProfitMap[char]) charProfitMap[char] = { profit: 0, items: 0 };
      if (d.status === 'sold') {
        charProfitMap[char].profit += ((d.soldPrice || 0) - (d.purchasePrice || 0));
      }
      charProfitMap[char].items++;
    });

    const sortedChars = Object.keys(charProfitMap).map(c => ({
      character: c,
      profit: charProfitMap[c].profit,
      items: charProfitMap[c].items
    })).sort((a, b) => b.profit - a.profit);

    const leaderContainer = document.getElementById('leaderboard-container');
    leaderContainer.innerHTML = '';

    const medals = ['🥇', '🥈', '🥉'];
    sortedChars.slice(0, 3).forEach((item, idx) => {
      const card = document.createElement('div');
      card.className = 'leaderboard-card';
      card.innerHTML = `
        <div class="rank-badge">${medals[idx] || '⭐'}</div>
        <div>
          <div style="font-weight: 700; font-size: 1rem; color: var(--text-white);">${item.character}</div>
          <div style="font-size: 0.8rem; color: var(--gold-accent); font-weight: 700;">Lucro: +€${item.profit.toFixed(2)}</div>
          <div style="font-size: 0.72rem; color: var(--text-muted);">${item.items} bonecas registadas</div>
        </div>
      `;
      leaderContainer.appendChild(card);
    });

    const canvas = document.getElementById('chart-networth');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const personal = this.dolls.filter(d => d.status === 'personal');
    const batchMap = this.getBatchAmortizationMap();

    let totMkt = personal.reduce((sum, d) => sum + (d.purchasePrice || 0), 0);
    let totEffCost = personal.reduce((sum, d) => {
      let eff = d.purchasePrice || 0;
      if (d.batchId && batchMap[d.batchId]) eff = Math.max(0, eff - batchMap[d.batchId].soldRevenue);
      return sum + eff;
    }, 0);

    const barWidth = 140;
    const maxVal = Math.max(totMkt, totEffCost, 100);

    const h1 = (totMkt / maxVal) * 160;
    ctx.fillStyle = '#00F5D4';
    ctx.fillRect(200, 200 - h1, barWidth, h1);

    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 14px Outfit';
    ctx.fillText(`Custo Inicial: €${totMkt.toFixed(2)}`, 190, 190 - h1);

    const h2 = (totEffCost / maxVal) * 160;
    ctx.fillStyle = '#FF007F';
    ctx.fillRect(400, 200 - h2, barWidth, h2);

    ctx.fillStyle = '#FFFFFF';
    ctx.fillText(`Custo Efetivo: €${totEffCost.toFixed(2)}`, 390, 190 - h2);

    ctx.strokeStyle = '#30223D';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(100, 200);
    ctx.lineTo(600, 200);
    ctx.stroke();
  }

  generateTradingCard(dollId) {
    const d = this.dolls.find(item => item.id === dollId);
    if (!d) return;

    this.selectedCardDollId = dollId;
    const canvas = document.getElementById('trading-card-canvas');
    const ctx = canvas.getContext('2d');

    const grad = ctx.createLinearGradient(0, 0, 600, 800);
    grad.addColorStop(0, '#160D24');
    grad.addColorStop(1, '#0D0814');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 600, 800);

    ctx.strokeStyle = '#FF007F';
    ctx.lineWidth = 8;
    ctx.strokeRect(20, 20, 560, 760);

    ctx.strokeStyle = '#00F5D4';
    ctx.lineWidth = 2;
    ctx.strokeRect(28, 28, 544, 744);

    ctx.fillStyle = '#FF007F';
    ctx.font = 'bold 28px Outfit';
    ctx.textAlign = 'center';
    ctx.fillText("MONSTER HIGH COLLECTION", 300, 70);

    ctx.fillStyle = '#00F5D4';
    ctx.font = 'bold 20px Outfit';
    ctx.fillText(d.line || "Signature Series", 300, 100);

    ctx.fillStyle = '#1A1124';
    ctx.fillRect(100, 130, 400, 360);
    ctx.strokeStyle = '#9C27B0';
    ctx.lineWidth = 4;
    ctx.strokeRect(100, 130, 400, 360);

    if (d.photoUrl) {
      const img = new Image();
      img.onload = () => {
        ctx.drawImage(img, 105, 135, 390, 350);
        this._finishTradingCardText(ctx, d);
      };
      img.src = d.photoUrl;
    } else {
      ctx.fillStyle = '#B3A4C4';
      ctx.font = '70px Segoe UI';
      ctx.fillText("🧟‍♀️", 300, 320);
      this._finishTradingCardText(ctx, d);
    }

    document.getElementById('modal-card').classList.add('active');
  }

  _finishTradingCardText(ctx, d) {
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 32px Outfit';
    ctx.textAlign = 'center';
    ctx.fillText(d.name, 300, 540);

    ctx.fillStyle = '#B3A4C4';
    ctx.font = '18px Inter';
    ctx.fillText(`Condição: ${d.condition || 'NIB'} • Penteado: ${d.hairstyleDifficulty || 'Simples'}`, 300, 575);

    ctx.fillStyle = '#FF007F';
    ctx.fillRect(120, 610, 360, 60);

    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 22px Outfit';
    ctx.fillText("✨ 0.00€ COLLECTION ASSET ✨", 300, 648);

    ctx.fillStyle = '#00F5D4';
    ctx.font = 'bold 16px Inter';
    ctx.fillText(`Linha: ${d.line || 'Monster High'}`, 300, 710);

    ctx.fillStyle = '#7D6E91';
    ctx.font = '12px Inter';
    ctx.fillText("MONSTER HIGH STOCK MANAGER PRO • PWA", 300, 750);
  }

  downloadTradingCard() {
    const canvas = document.getElementById('trading-card-canvas');
    const link = document.createElement('a');
    link.download = `mh_card_${this.selectedCardDollId || 'collection'}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  }

  closeCardModal() {
    document.getElementById('modal-card').classList.remove('active');
  }

  // --- RENDER VIRTUAL SHELF WITH INSTANT LIVE PHOTO REFRESH ---
  renderVirtualShelf() {
    const container = document.getElementById('virtual-shelf-grid');
    if (!container) return;
    container.innerHTML = '';

    const personal = this.dolls.filter(d => d.status === 'personal');
    const batchMap = this.getBatchAmortizationMap();

    let totCost = 0;

    if (personal.length === 0) {
      container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;">Ainda não tem bonecas na sua Coleção Própria. Marque bonecas como "Coleção Própria 🟣" para expor na sua estante virtual!</div>`;
      return;
    }

    personal.forEach(d => {
      let effCost = d.purchasePrice || 0;
      if (d.batchId && batchMap[d.batchId]) {
        effCost = Math.max(0, effCost - batchMap[d.batchId].soldRevenue);
      }
      totCost += effCost;

      const item = document.createElement('div');
      item.className = 'shelf-doll-item';
      item.onclick = () => this.openDollModal(d.id);

      const photoHtml = d.photoUrl 
        ? `<img src="${d.photoUrl}" class="shelf-doll-img" alt="${d.name}">`
        : `<div class="shelf-doll-img-placeholder">🧟‍♀️</div>`;

      item.innerHTML = `
        ${photoHtml}
        <div style="font-weight: 700; font-size: 0.95rem; color: var(--text-white); margin-bottom: 4px;">${d.name}</div>
        <div style="font-size: 0.75rem; color: var(--cyan-mint); font-weight: 600;">${d.line || 'Monster High'}</div>
        ${d.hairstyleDifficulty ? `<div style="font-size: 0.72rem; color: var(--purple-electric); margin-top: 2px;">💇‍♀️ Penteado: ${d.hairstyleDifficulty}</div>` : ''}
        ${d.batchId ? `<div style="font-size: 0.72rem; color: var(--text-dim); margin-top: 2px;">📦 Lote: ${d.batchId}</div>` : ''}
        
        <div style="margin-top: 8px; font-size: 0.8rem;">
          <span style="color: var(--pink-neon); font-weight: 800;">${effCost === 0 ? '✨ 0.00€ AMORTIZADA' : 'Custo Ef.: €' + effCost.toFixed(2)}</span>
        </div>

        <div style="display: flex; gap: 4px; margin-top: 10px; flex-wrap: wrap;" onclick="event.stopPropagation();">
          <button class="btn btn-cyan" style="flex: 1; padding: 5px 6px; font-size: 0.73rem;" onclick="app.moveToResale(${d.id})">🟢 Pôr à Venda</button>
          <button class="btn btn-outline" style="padding: 5px 6px; font-size: 0.73rem;" onclick="app.openDollModal(${d.id})">✏️ Editar</button>
          <button class="btn btn-purple" style="padding: 5px 6px; font-size: 0.73rem;" onclick="app.generateTradingCard(${d.id})">🖼️ Card</button>
        </div>
      `;

      container.appendChild(item);
    });

    const costEl = document.getElementById('shelf-cost-val');
    if (costEl) costEl.textContent = `€${totCost.toFixed(2)}`;
  }

  renderWishlist() {
    const container = document.getElementById('wishlist-container');
    container.innerHTML = '';

    if (this.wishlist.length === 0) {
      container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;">Sua Lista de Caça está vazia. Adicione bonecas que pretende comprar!</div>`;
      return;
    }

    this.wishlist.forEach((w, idx) => {
      const card = document.createElement('div');
      card.className = 'wishlist-card';
      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div style="font-weight: 700; font-size: 1rem; color: var(--text-white);">${w.name}</div>
          <span class="badge badge-personal">${w.priority}</span>
        </div>
        <div style="font-size: 0.85rem; color: var(--cyan-mint); margin: 8px 0;">Preço Máx. Alvo: <strong>€${(w.maxPrice || 0).toFixed(2)}</strong></div>
        <div style="font-size: 0.75rem; color: var(--text-muted);">Dica: Ao comprar um lote de 3 unidades a €${((w.maxPrice || 0)*3).toFixed(2)}, esta fica a 0.00€ se vender 2 a €${((w.maxPrice || 0)*1.5).toFixed(2)}!</div>
        <button class="btn btn-outline" style="margin-top: 10px; width: 100%; color: var(--red-accent);" onclick="app.deleteWishlist(${idx})">🗑️ Remover da Caça</button>
      `;
      container.appendChild(card);
    });
  }

  deleteWishlist(idx) {
    this.wishlist.splice(idx, 1);
    this.saveState();
    this.renderWishlist();
  }

  copyVintedAd(id) {
    const d = this.dolls.find(item => item.id === id);
    if (!d) return;

    const adText = `🧟‍♀️ Monster High ${d.name} (${d.line || 'Coleção'})\n` +
      `Condição: ${d.condition || 'Excelente'}\n` +
      `Penteado: ${d.hairstyleDifficulty || 'Padrão'}\n` +
      `Acessórios: ${d.notes || 'Completa em ótimo estado de conservação.'}\n` +
      `📦 Envio rápido e extremamente bem protegido em caixa reforçada com plástico bolha!\n` +
      `Qualquer dúvida estou à disposição! ✨`;

    navigator.clipboard.writeText(adText).then(() => {
      alert(`📋 Anúncio Vinted/OLX para '${d.name}' copiado para a área de transferência! Basta colar na app da Vinted.`);
    }).catch(() => {
      alert(`Texto do Anúncio:\n\n${adText}`);
    });
  }

  openSellModal(id) {
    const d = this.dolls.find(item => item.id === id);
    if (!d) return;

    document.getElementById('sell-doll-id').value = id;
    document.getElementById('sell-price-input').value = d.sellingPrice || 45.00;
    document.getElementById('modal-sell').classList.add('active');
    this.updateSellFeePreview();
  }

  closeSellModal() {
    document.getElementById('modal-sell').classList.remove('active');
  }

  updateSellFeePreview() {
    const platform = document.getElementById('sell-platform').value;
    const price = parseFloat(document.getElementById('sell-price-input').value) || 0;
    let net = price;

    if (platform === 'ebay') {
      net = price * 0.872;
    }

    document.getElementById('sell-net-preview').textContent = `💵 Lucro Líquido Estimado a receber: €${net.toFixed(2)}`;
  }

  handleSellSubmit(e) {
    e.preventDefault();
    const id = parseInt(document.getElementById('sell-doll-id').value);
    const d = this.dolls.find(item => item.id === id);

    if (d) {
      const soldP = parseFloat(document.getElementById('sell-price-input').value) || 0;
      d.status = 'sold';
      d.soldPrice = soldP;
      this.saveState();
      this.closeSellModal();

      if (d.batchId) {
        const batchMap = this.getBatchAmortizationMap();
        const bInfo = batchMap[d.batchId];

        if (bInfo && bInfo.soldRevenue >= bInfo.totalCost) {
          if (typeof confetti === 'function') {
            confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } });
          }
          if (navigator.vibrate) {
            navigator.vibrate([100, 50, 100, 50, 200]);
          }
          alert(`🎉 PARABÉNS! A venda do Lote ${d.batchId} cobriu 100% dos custos!\nA sua boneca de coleção ficou a 0.00€! 💖`);
        }
      }
    }
  }

  openDollModal(editId = null) {
    const modal = document.getElementById('modal-doll');
    const title = document.getElementById('doll-modal-title');
    document.getElementById('edit-doll-id').value = editId || '';
    this.currentPhotoBase64 = null;
    document.getElementById('photo-preview-container').style.display = 'none';

    if (editId) {
      title.textContent = 'Editar Boneca / Fotografias & Detalhes';
      const d = this.dolls.find(item => item.id === editId);
      if (d) {
        document.getElementById('form-name').value = d.name || '';
        document.getElementById('form-char').value = d.character || '';
        document.getElementById('form-line').value = d.line || COLLECTIONS[0];
        document.getElementById('form-cond').value = d.condition || 'NIB';
        document.getElementById('form-status').value = d.status || 'in_stock';
        document.getElementById('form-purchase').value = d.purchasePrice || '';
        document.getElementById('form-sell').value = d.status === 'personal' ? '0.00' : (d.sellingPrice || '');
        document.getElementById('form-sold').value = d.soldPrice || '';
        document.getElementById('form-batch').value = d.batchId || '';
        document.getElementById('form-notes').value = d.notes || '';
        document.getElementById('form-hairstyle').value = d.hairstyleDifficulty || 'Simples 🟢';
        
        if (d.photoUrl) {
          this.currentPhotoBase64 = d.photoUrl;
          document.getElementById('photo-preview-img').src = d.photoUrl;
          document.getElementById('photo-preview-container').style.display = 'block';
        }
      }
    } else {
      title.textContent = 'Adicionar Nova Boneca';
      document.getElementById('doll-form').reset();
    }

    this.onFormStatusChange();
    modal.classList.add('active');
  }

  closeDollModal() {
    document.getElementById('modal-doll').classList.remove('active');
  }

  handleDollSubmit(e) {
    e.preventDefault();
    const editId = parseInt(document.getElementById('edit-doll-id').value);

    const restoreExtra = parseFloat(document.getElementById('form-restore-cost').value) || 0;
    const basePurchase = parseFloat(document.getElementById('form-purchase').value) || 0;
    const statusVal = document.getElementById('form-status').value;

    let finalPhoto = this.currentPhotoBase64;
    if (!finalPhoto && editId) {
      const existing = this.dolls.find(d => d.id === editId);
      if (existing) finalPhoto = existing.photoUrl;
    }

    const dollData = {
      name: document.getElementById('form-name').value.trim(),
      character: document.getElementById('form-char').value.trim(),
      line: document.getElementById('form-line').value,
      condition: document.getElementById('form-cond').value,
      status: statusVal,
      purchasePrice: basePurchase + restoreExtra,
      sellingPrice: statusVal === 'personal' ? 0.00 : (parseFloat(document.getElementById('form-sell').value) || 0),
      soldPrice: statusVal === 'personal' ? null : (parseFloat(document.getElementById('form-sold').value) || null),
      batchId: document.getElementById('form-batch').value.trim() || null,
      notes: document.getElementById('form-notes').value.trim() || '',
      hairstyleDifficulty: document.getElementById('form-hairstyle').value,
      photoUrl: finalPhoto || null
    };

    if (editId) {
      const idx = this.dolls.findIndex(d => d.id === editId);
      if (idx !== -1) {
        this.dolls[idx] = { ...this.dolls[idx], ...dollData };
      }
    } else {
      const newId = this.dolls.length > 0 ? Math.max(...this.dolls.map(d => d.id)) + 1 : 1;
      this.dolls.push({ id: newId, ...dollData });
    }

    this.saveState();
    this.closeDollModal();
  }

  moveToPersonal(id) {
    const d = this.dolls.find(item => item.id === id);
    if (d) {
      d.status = 'personal';
      d.sellingPrice = 0.00;
      d.soldPrice = null;
      this.saveState();
    }
  }

  // --- MOVE PERSONAL COLLECTION DOLL TO RESALE STOCK ---
  moveToResale(id) {
    const d = this.dolls.find(item => item.id === id);
    if (!d) return;

    const defaultEst = d.purchasePrice ? (d.purchasePrice * 1.5).toFixed(2) : "45.00";
    const estPriceStr = prompt(`Qual o Preço Estimado de Venda (€) para colocar '${d.name}' à venda?`, defaultEst);
    if (estPriceStr === null) return; // User cancelled

    const estPrice = parseFloat(estPriceStr.replace(',', '.')) || 0;
    d.status = 'in_stock';
    d.sellingPrice = estPrice;
    d.soldPrice = null;

    this.saveState();
    alert(`🟢 '${d.name}' foi colocada à venda por €${estPrice.toFixed(2)} e movida para a aba Stock & Revenda!`);
  }

  deleteDoll(id) {
    if (confirm('Tem a certeza que pretende eliminar esta boneca?')) {
      this.dolls = this.dolls.filter(d => d.id !== id);
      this.saveState();
    }
  }

  openBatchModal() {
    document.getElementById('modal-batch').classList.add('active');
    this.updateBatchPreview();
  }

  closeBatchModal() {
    document.getElementById('modal-batch').classList.remove('active');
  }

  updateBatchPreview() {
    const totalCost = parseFloat(document.getElementById('batch-total-cost').value) || 0;
    const shipping = parseFloat(document.getElementById('batch-shipping').value) || 0;
    const grandCost = totalCost + shipping;

    const totalUnits = parseInt(document.getElementById('batch-total-units').value) || 1;
    const personalUnits = parseInt(document.getElementById('batch-personal-units').value) || 0;
    const resaleUnits = Math.max(0, totalUnits - personalUnits);

    const customEstInput = document.getElementById('batch-est-sell-price').value.replace(',', '.');
    const customEstPrice = parseFloat(customEstInput);

    const preview = document.getElementById('batch-calc-preview');

    if (resaleUnits > 0 && grandCost > 0) {
      const recPrice = grandCost / resaleUnits;
      const unitCost = grandCost / totalUnits;

      if (!isNaN(customEstPrice) && customEstPrice > 0) {
        const totalEstRev = customEstPrice * resaleUnits;
        const personalInitialCost = unitCost * personalUnits;
        const effCost = Math.max(0, personalInitialCost - (totalEstRev - (grandCost - personalInitialCost)));
        preview.textContent = `🎯 Estimativa Escolhida: €${customEstPrice.toFixed(2)} / un. -> Receita Revenda: €${totalEstRev.toFixed(2)} | Custo Ef. Coleção: €${effCost.toFixed(2)}`;
      } else {
        preview.textContent = `💡 Sugestão para amortizar a 100%: €${recPrice.toFixed(2)} / un. (ou digite o seu valor no campo acima)`;
      }
    } else {
      preview.textContent = `Preencha os valores do lote para ver a estimativa recomendada.`;
    }
  }

  handleBatchSubmit(e) {
    e.preventDefault();
    const nameModel = document.getElementById('batch-name').value.trim();
    const totalUnits = parseInt(document.getElementById('batch-total-units').value) || 1;
    const personalUnits = parseInt(document.getElementById('batch-personal-units').value) || 0;
    const totalCost = parseFloat(document.getElementById('batch-total-cost').value) || 0;
    const shipping = parseFloat(document.getElementById('batch-shipping').value) || 0;

    const grandCost = totalCost + shipping;
    const resaleUnits = Math.max(0, totalUnits - personalUnits);
    const unitCost = grandCost / totalUnits;

    const customEstInput = document.getElementById('batch-est-sell-price').value.replace(',', '.');
    const customEstPrice = parseFloat(customEstInput);

    const targetResalePrice = (!isNaN(customEstPrice) && customEstPrice > 0) ? customEstPrice : (resaleUnits > 0 ? (grandCost / resaleUnits) : unitCost);

    const batchId = this.getNextBatchId(nameModel);
    let nextId = this.dolls.length > 0 ? Math.max(...this.dolls.map(d => d.id)) + 1 : 1;

    for (let i = 0; i < personalUnits; i++) {
      this.dolls.push({
        id: nextId++,
        name: `${nameModel} (Coleção)`,
        character: nameModel.split(' ')[0] || nameModel,
        line: 'Creeproduction',
        condition: 'NIB',
        status: 'personal',
        purchasePrice: unitCost,
        sellingPrice: 0.00,
        soldPrice: null,
        batchId: batchId,
        notes: `Criado no Lote ${batchId}`,
        hairstyleDifficulty: "Simples 🟢",
        photoUrl: null
      });
    }

    for (let i = 0; i < resaleUnits; i++) {
      this.dolls.push({
        id: nextId++,
        name: `${nameModel} (Revenda #${i+1})`,
        character: nameModel.split(' ')[0] || nameModel,
        line: 'Creeproduction',
        condition: 'NIB',
        status: 'in_stock',
        purchasePrice: unitCost,
        sellingPrice: targetResalePrice,
        soldPrice: null,
        batchId: batchId,
        notes: `Criado no Lote ${batchId}`,
        hairstyleDifficulty: "Simples 🟢",
        photoUrl: null
      });
    }

    this.saveState();
    this.closeBatchModal();
    alert(`Lote '${batchId}' criado com sucesso!\n${personalUnits}x Coleção Própria + ${resaleUnits}x Revenda adicionadas com Est. Venda de €${targetResalePrice.toFixed(2)} / un.`);
  }

  openWishlistModal() {
    document.getElementById('modal-wishlist').classList.add('active');
  }

  closeWishlistModal() {
    document.getElementById('modal-wishlist').classList.remove('active');
  }

  handleWishlistSubmit(e) {
    e.preventDefault();
    const name = document.getElementById('wish-name').value.trim();
    const maxPrice = parseFloat(document.getElementById('wish-max-price').value) || 0;
    const priority = document.getElementById('wish-priority').value;

    const newId = this.wishlist.length > 0 ? Math.max(...this.wishlist.map(w => w.id)) + 1 : 1;
    this.wishlist.push({ id: newId, name, maxPrice, priority });

    this.saveState();
    this.closeWishlistModal();
    this.renderWishlist();
  }

  exportCSV() {
    let csv = 'ID,Nome,Personagem,Linha,Condicao,Estado,Penteado,Custo_Compra,Est_Venda,Preco_Vendido,Lote_ID\n';
    this.dolls.forEach(d => {
      csv += `${d.id},"${d.name}","${d.character || ''}","${d.line || ''}","${d.condition || ''}",${d.status},"${d.hairstyleDifficulty || ''}",${d.purchasePrice || 0},${d.sellingPrice || 0},${d.soldPrice || 0},"${d.batchId || ''}"\n`;
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.setAttribute('download', `monster_high_stock_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

// Clear old cache keys from localStorage if present
try {
  localStorage.removeItem('mh_stock_data_v15');
  localStorage.removeItem('mh_stock_data_v14');
  localStorage.removeItem('mh_stock_data_v13');
  localStorage.removeItem('mh_stock_data_v12');
  localStorage.removeItem('mh_stock_data_v11');
  localStorage.removeItem('mh_stock_data_v10');
  localStorage.removeItem('mh_stock_data_v9');
  localStorage.removeItem('mh_stock_data_v8');
  localStorage.removeItem('mh_stock_data_v7');
  localStorage.removeItem('mh_stock_data_v6');
  localStorage.removeItem('mh_stock_data_v5');
  localStorage.removeItem('mh_stock_data_v4');
  localStorage.removeItem('mh_stock_data_v2');
  localStorage.removeItem('mh_stock_data_v1');
} catch(e) {}

// Global App Instance
const app = new MHStockApp();
