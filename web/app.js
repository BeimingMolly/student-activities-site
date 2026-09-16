const state = {
  items: [],
  loans: [],
  venueBookings: [],
  violationRecords: [],
  users: [],
  currentUser: null,
  repositoryFolders: [],
  repositoryDocuments: [],
  repositoryBreadcrumbs: [],
  repositoryCurrentFolder: null,
  repositoryRootFolderId: null,
  selectedRepositoryEntry: null,
  activeRepositoryFolderId: null,
  activeRepositoryDocumentId: null,
  confirmResolver: null,
  pagination: {
    loans: 1,
    violations: 1,
  },
  inventoryChartSnapshots: {},
  inventoryChartTargets: {},
  inventoryChartExpanded: {},
  calendarDate: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
  datePickerMonth: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
  activeDateInput: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
const VENUE_SLOTS = [
  { label: "08:00~12:00", start: "08:00", end: "12:00", value: "08:00|12:00" },
  { label: "14:00~17:00", start: "14:00", end: "17:00", value: "14:00|17:00" },
  { label: "19:00~22:00", start: "19:00", end: "22:00", value: "19:00|22:00" },
];
const MATERIAL_TIMES = ["12:40", "17:30", "21:00"];
const QUICK_LOAN_ITEM_NAMES = ["折叠桌", "海报板", "帐篷", "塑料椅"];
const MATRIX_TEXT = "华侨大学学生办事大厅";
const MATRIX_THEME_STORAGE_KEY = "studentActivitiesMatrixTheme";
const CHART_COLLAPSED_LIMIT = 4;
const TABLE_PAGE_SIZE = 15;
const TEXT_PREVIEW_EXTENSIONS = new Set(["txt", "md", "csv", "json"]);
const OFFICE_EXTENSIONS = new Set(["doc", "docx", "xls", "xlsx", "ppt", "pptx"]);

function today() {
  return formatDate(new Date());
}

function formatDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatMonth(date) {
  return `${date.getFullYear()}年${date.getMonth() + 1}月`;
}

function formatShortDate(dateValue) {
  const [, month, day] = dateValue.split("-");
  return `${Number(month)}/${Number(day)}`;
}

function formatDateTime(dateValue, timeValue) {
  if (!dateValue) return "未填写";
  return timeValue ? `${dateValue} ${timeValue}` : dateValue;
}

function parseDateValue(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(value || ""))) return new Date();
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function getWeekStart(date) {
  const offset = (date.getDay() + 6) % 7;
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() - offset);
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2400);
}

function syncModalOpenState() {
  document.body.classList.toggle("modal-open", $$(".modal-backdrop").some((modal) => !modal.hidden));
}

function openSuccessModal(message) {
  $("#successModalMessage").textContent = message;
  $("#successModal").hidden = false;
  document.body.classList.add("modal-open");
}

function closeSuccessModal() {
  $("#successModal").hidden = true;
  syncModalOpenState();
}

function openConfirmModal(message, confirmText = "删除") {
  $("#confirmModalMessage").textContent = message;
  $("#acceptConfirmModalButton").textContent = confirmText;
  $("#confirmModal").hidden = false;
  document.body.classList.add("modal-open");

  return new Promise((resolve) => {
    state.confirmResolver = resolve;
  });
}

function closeConfirmModal(accepted = false) {
  $("#confirmModal").hidden = true;
  const resolver = state.confirmResolver;
  state.confirmResolver = null;
  syncModalOpenState();
  if (resolver) resolver(accepted);
}

function renderMatrixBackground() {
  const matrix = $("#matrixBackground");
  if (!matrix) return;

  const cellCount = Math.ceil((1920 / 40) * (1080 / 40));
  const chars = Array.from(MATRIX_TEXT);
  matrix.innerHTML = Array.from({ length: cellCount })
    .map((_, index) => `<span>${chars[index % chars.length]}</span>`)
    .join("");
}

function getSavedMatrixTheme() {
  try {
    return localStorage.getItem(MATRIX_THEME_STORAGE_KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

function setMatrixTheme(theme) {
  const isDark = theme === "dark";
  document.body.classList.toggle("matrix-dark", isDark);

  const toggleButton = $("#themeToggleButton");
  if (toggleButton) {
    const label = isDark ? "白色背景" : "深色背景";
    const tooltip = isDark ? "切换为白色背景" : "切换为深色背景";
    const text = toggleButton.querySelector(".theme-toggle-text");
    const tooltipText = toggleButton.querySelector(".theme-toggle-tooltip-text");
    if (text) text.textContent = label;
    if (tooltipText) tooltipText.textContent = tooltip;
    toggleButton.title = isDark ? "切换为白色背景" : "切换为深色背景";
    toggleButton.dataset.tooltip = tooltip;
    toggleButton.setAttribute("aria-pressed", String(isDark));
  }

  try {
    localStorage.setItem(MATRIX_THEME_STORAGE_KEY, isDark ? "dark" : "light");
  } catch {
    // 浏览器禁用本地存储时，只保留本次页面里的切换效果。
  }
}

function toggleMatrixTheme() {
  const nextTheme = document.body.classList.contains("matrix-dark") ? "light" : "dark";
  setMatrixTheme(nextTheme);
  showToast(nextTheme === "dark" ? "已切换为深色背景" : "已切换为白色背景");
}

function positionDatePicker(input) {
  const picker = $("#customDatePicker");
  const rect = input.getBoundingClientRect();
  const gap = 8;
  const pickerWidth = 272;
  const left = Math.min(rect.left, window.innerWidth - pickerWidth - 12);
  const top = Math.min(rect.bottom + gap, window.innerHeight - 360);

  picker.style.left = `${Math.max(12, left)}px`;
  picker.style.top = `${Math.max(12, top)}px`;
}

function renderDatePicker() {
  const picker = $("#customDatePicker");
  const input = state.activeDateInput || $("#inventorySnapshotDate");
  const selectedDate = parseDateValue(input.value || today());
  const monthDate = state.datePickerMonth;
  const year = monthDate.getFullYear();
  const month = monthDate.getMonth();
  const firstDay = new Date(year, month, 1);
  const leadingDays = (firstDay.getDay() + 6) % 7;
  const cells = Array.from({ length: 42 }).map((_, index) => {
    const date = new Date(year, month, 1 - leadingDays + index);
    const dateValue = formatDate(date);
    const isSelected = dateValue === formatDate(selectedDate);
    const isToday = dateValue === today();
    const isOutside = date.getMonth() !== month;
    const className = [
      "date-picker-day",
      isSelected ? "selected" : "",
      isToday ? "today" : "",
      isOutside ? "outside-month" : "",
    ]
      .filter(Boolean)
      .join(" ");

    return `<button class="${className}" type="button" data-date-value="${dateValue}">${date.getDate()}</button>`;
  }).join("");

  picker.innerHTML = `
    <div class="date-picker-header">
      <button class="date-picker-nav" type="button" data-date-nav="-1" aria-label="上个月">‹</button>
      <strong class="date-picker-month">${formatMonth(monthDate)}</strong>
      <button class="date-picker-nav" type="button" data-date-nav="1" aria-label="下个月">›</button>
    </div>
    <div class="date-picker-weekdays" aria-hidden="true">
      <span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span><span>日</span>
    </div>
    <div class="date-picker-grid">${cells}</div>
    <div class="date-picker-footer">
      <button class="date-picker-link" type="button" data-date-clear>清除</button>
      <button class="date-picker-link" type="button" data-date-today>今天</button>
    </div>
  `;
}

function openDatePicker(input) {
  state.activeDateInput = input;
  const selectedDate = parseDateValue(input.value || today());
  state.datePickerMonth = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1);
  renderDatePicker();
  positionDatePicker(input);
  $("#customDatePicker").hidden = false;
}

function closeDatePicker() {
  $("#customDatePicker").hidden = true;
  state.activeDateInput = null;
}

function setPickedDate(dateValue) {
  const input = state.activeDateInput;
  if (!input) return;
  input.value = dateValue;
  closeDatePicker();
  input.dispatchEvent(new Event("change", { bubbles: true }));
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const isJson = response.headers.get("Content-Type")?.includes("application/json");
  const data = isJson ? await response.json() : {};
  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error(data.error || "请先登录。");
  }
  if (!response.ok) {
    throw new Error(data.error || "请求失败");
  }
  return data;
}

function formPayload(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[char];
  });
}

function fileExtension(filename = "") {
  const parts = String(filename).split(".");
  return parts.length > 1 ? parts.pop().toLowerCase() : "";
}

function formatFileSize(bytes) {
  const size = Number(bytes) || 0;
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`;
  if (size >= 1024) return `${Math.ceil(size / 1024)} KB`;
  return `${size} B`;
}

function documentPreviewType(document) {
  const extension = fileExtension(document.original_name);
  const mimeType = document.mime_type || "";
  if (mimeType.startsWith("image/")) return "image";
  if (extension === "pdf" || mimeType === "application/pdf") return "pdf";
  if (TEXT_PREVIEW_EXTENSIONS.has(extension) || mimeType.startsWith("text/")) return "text";
  if (OFFICE_EXTENSIONS.has(extension)) return "office";
  return "unsupported";
}

function paginationInfo(key, total) {
  const pageCount = Math.max(Math.ceil(total / TABLE_PAGE_SIZE), 1);
  const currentPage = Math.min(Math.max(Number(state.pagination[key]) || 1, 1), pageCount);
  state.pagination[key] = currentPage;

  return {
    currentPage,
    pageCount,
    start: (currentPage - 1) * TABLE_PAGE_SIZE,
    end: Math.min(currentPage * TABLE_PAGE_SIZE, total),
  };
}

function pageNumbers(currentPage, pageCount) {
  if (pageCount <= 7) {
    return Array.from({ length: pageCount }, (_, index) => index + 1);
  }

  const pages = new Set([1, pageCount, currentPage - 1, currentPage, currentPage + 1]);
  return Array.from(pages)
    .filter((page) => page >= 1 && page <= pageCount)
    .sort((a, b) => a - b)
    .reduce((result, page, index, pagesList) => {
      if (index > 0 && page - pagesList[index - 1] > 1) {
        result.push("gap");
      }
      result.push(page);
      return result;
    }, []);
}

function renderPagination(targetSelector, key, total) {
  const container = $(targetSelector);
  if (!container) return;

  if (total <= 0) {
    container.innerHTML = "";
    return;
  }

  const { currentPage, pageCount, start, end } = paginationInfo(key, total);
  const buttons = pageNumbers(currentPage, pageCount)
    .map((page) => {
      if (page === "gap") return '<span class="pagination-gap">...</span>';
      return `
        <button
          class="pagination-page-button ${page === currentPage ? "active" : ""}"
          type="button"
          data-page-key="${key}"
          data-page-number="${page}"
        >
          ${page}
        </button>
      `;
    })
    .join("");

  container.innerHTML = `
    <span class="pagination-info">共 ${total} 条，显示 ${start + 1}-${end} 条，每页 ${TABLE_PAGE_SIZE} 条</span>
    <div class="pagination-buttons">
      <button
        class="inline-button"
        type="button"
        data-page-key="${key}"
        data-page-number="${currentPage - 1}"
        ${currentPage === 1 ? "disabled" : ""}
      >
        上一页
      </button>
      ${buttons}
      <button
        class="inline-button"
        type="button"
        data-page-key="${key}"
        data-page-number="${currentPage + 1}"
        ${currentPage === pageCount ? "disabled" : ""}
      >
        下一页
      </button>
    </div>
  `;
}

function statusPill(value) {
  const labels = {
    Available: "可用",
    Borrowed: "借出中",
    Returned: "已归还",
    "In Use": "使用中",
    Booked: "已预约",
    Cancelled: "已取消",
  };
  const className = ["Available", "Returned", "Booked"].includes(value) ? "pill" : "pill warn";
  return `<span class="${className}">${labels[value] || value}</span>`;
}

function loanReturnStatus(loan) {
  const dueDate = loan.due_date || "";
  const dueTime = loan.due_time || "23:59";
  const dueAt = new Date(`${dueDate}T${dueTime}`);
  if (Number.isNaN(dueAt.getTime())) return statusPill("Borrowed");

  return new Date() > dueAt ? statusPill("Returned") : statusPill("Borrowed");
}

function loanCountsInInventory(loan) {
  if (!loan) return false;

  const loanAt = new Date(`${loan.loan_date || ""}T${loan.loan_time || "00:00"}`);
  const dueAt = new Date(`${loan.due_date || ""}T${loan.due_time || "23:59"}`);
  if (Number.isNaN(loanAt.getTime()) || Number.isNaN(dueAt.getTime())) return false;

  const now = new Date();
  return loanAt <= now && now < dueAt;
}

function setActiveView(viewId) {
  if (viewId === "userManagementView" && !state.currentUser?.is_admin) {
    viewId = "homeView";
  }
  const view = document.getElementById(viewId);
  if (!view) return;

  $$(".view").forEach((item) => item.classList.toggle("active", item.id === viewId));
  $$('input[name="mainNav"]').forEach((input) => {
    input.checked = input.dataset.viewTarget === viewId;
  });

  $("#viewTitle").textContent = view.dataset.title;
  $("#viewEyebrow").textContent = view.dataset.eyebrow;
}

function configureAdminNavigation() {
  const canManageUsers = Boolean(state.currentUser?.is_admin);
  const nav = $(".side-nav");
  document.body.classList.toggle("admin-user", canManageUsers);
  nav.style.setProperty("--total-radio", canManageUsers ? "7" : "6");

  if (!canManageUsers && $("#navUsers").checked) {
    setActiveView("homeView");
  }
}

function renderStats(stats) {
  const targets = {
    itemCount: stats.item_count,
    venueCount: stats.venue_count,
    activeLoans: stats.active_loans,
    lowStock: stats.low_stock,
  };

  Object.entries(targets).forEach(([id, value]) => {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  });
}

function loanItemQuantityMap(loan = null) {
  return new Map((loan?.loan_items || []).map((item) => [Number(item.item_id), Number(item.quantity) || 0]));
}

function editableAvailableQuantity(item, existingQuantity, loan = null) {
  return loanCountsInInventory(loan) ? item.available_quantity + existingQuantity : item.available_quantity;
}

function renderLoanMaterialControls(loan = null) {
  const quantities = loanItemQuantityMap(loan);
  const quickGrid = $("#quickMaterialGrid");
  const stockOtherSelect = $("#stockOtherItemSelect");
  const stockOtherQuantityInput = $("#stockOtherQuantityInput");
  const quickNameSet = new Set(QUICK_LOAN_ITEM_NAMES);

  quickGrid.innerHTML = QUICK_LOAN_ITEM_NAMES.map((name) => {
    const item = state.items.find((entry) => entry.name === name);
    if (!item) {
      return `
        <label class="material-quantity-card unavailable">
          <span class="material-name">${escapeHtml(name)}</span>
          <span class="material-meta">未入库</span>
          <input type="number" min="0" value="0" disabled />
        </label>
      `;
    }

    const existingQuantity = quantities.get(Number(item.id)) || 0;
    const availableQuantity = editableAvailableQuantity(item, existingQuantity, loan);
    return `
      <label class="material-quantity-card">
        <span class="material-name">${escapeHtml(item.name)}</span>
        <span class="material-meta">可用 ${availableQuantity} ${escapeHtml(item.unit)}</span>
        <input
          data-loan-item-id="${item.id}"
          data-loan-item-quantity
          type="number"
          min="0"
          step="1"
          value="${existingQuantity}"
          placeholder="0"
        />
      </label>
    `;
  }).join("");

  const stockOtherItems = state.items.filter((item) => !quickNameSet.has(item.name));
  const selectedOtherItem = (loan?.loan_items || []).find((item) => !quickNameSet.has(item.item_name));
  stockOtherSelect.innerHTML = '<option value="">请选择剩余物资</option>';
  stockOtherItems.forEach((item) => {
    const existingQuantity = selectedOtherItem && Number(selectedOtherItem.item_id) === Number(item.id)
      ? Number(selectedOtherItem.quantity) || 0
      : 0;
    const availableQuantity = editableAvailableQuantity(item, existingQuantity, loan);
    const disabled = availableQuantity <= 0 && existingQuantity === 0 ? "disabled" : "";
    const selected = existingQuantity > 0 ? "selected" : "";
    stockOtherSelect.insertAdjacentHTML(
      "beforeend",
      `<option value="${item.id}" ${disabled} ${selected}>${escapeHtml(item.name)}（可用 ${availableQuantity} ${escapeHtml(item.unit)}）</option>`,
    );
  });
  stockOtherQuantityInput.value = selectedOtherItem ? selectedOtherItem.quantity : 0;
}

function normalizeMaterialTime(value) {
  return MATERIAL_TIMES.includes(value) ? value : MATERIAL_TIMES[0];
}

function setRadioValue(form, fieldName, value) {
  const normalizedValue = normalizeMaterialTime(value);
  Array.from(form.querySelectorAll(`input[name="${fieldName}"]`)).forEach((input) => {
    input.checked = input.value === normalizedValue;
  });
}

function collectLoanItems() {
  const itemQuantities = new Map();

  $$("[data-loan-item-quantity]").forEach((input) => {
    const itemId = Number(input.dataset.loanItemId);
    const quantity = Number(input.value || 0);
    if (itemId && quantity > 0) {
      itemQuantities.set(itemId, (itemQuantities.get(itemId) || 0) + quantity);
    }
  });

  const stockOtherItemId = Number($("#stockOtherItemSelect").value || 0);
  const stockOtherQuantity = Number($("#stockOtherQuantityInput").value || 0);
  if (stockOtherQuantity > 0) {
    if (!stockOtherItemId) {
      throw new Error("请选择库存其他物资");
    }
    itemQuantities.set(stockOtherItemId, (itemQuantities.get(stockOtherItemId) || 0) + stockOtherQuantity);
  }

  return Array.from(itemQuantities.entries()).map(([itemId, quantity]) => ({
    item_id: itemId,
    quantity,
  }));
}

function renderItems() {
  if (state.items.length === 0) {
    $("#itemsBody").innerHTML = '<tr><td colspan="6" class="empty-cell">暂无物资库存</td></tr>';
    return;
  }

  $("#itemsBody").innerHTML = state.items
    .map((item) => {
      const availableClass = item.available_quantity <= 0 ? "danger" : item.available_quantity <= 2 ? "warn" : "";
      return `
        <tr>
          <td>${escapeHtml(item.name)}</td>
          <td>${escapeHtml(item.size || "无")}</td>
          <td>${item.total_quantity} ${escapeHtml(item.unit)}</td>
          <td>${item.borrowed_quantity} ${escapeHtml(item.unit)}</td>
          <td><span class="pill ${availableClass}">${item.available_quantity} ${escapeHtml(item.unit)}</span></td>
          <td><button class="inline-button" data-edit-item="${item.id}" type="button">修改</button></td>
        </tr>
      `;
    })
    .join("");
}

function renderLoans() {
  if (state.loans.length === 0) {
    $("#loansBody").innerHTML = '<tr><td colspan="8" class="empty-cell">暂无物资借出记录</td></tr>';
    $("#loansPagination").innerHTML = "";
    $("#selectAllLoans").checked = false;
    return;
  }

  const { start, end } = paginationInfo("loans", state.loans.length);
  $("#selectAllLoans").checked = false;
  $("#loansBody").innerHTML = state.loans
    .slice(start, end)
    .map(
      (loan) => {
        const isVenueLoan = Boolean(loan.source_venue_booking_id);
        return `
          <tr class="${isVenueLoan ? "venue-loan-row" : ""}">
            <td class="check-cell">
              ${isVenueLoan ? "" : `
                <label class="checkbox-container table-checkbox" title="选择借出记录">
                  <input class="custom-checkbox" type="checkbox" data-loan-check value="${loan.id}" aria-label="选择借出记录" />
                  <span class="checkmark"></span>
                </label>
              `}
            </td>
            <td>${escapeHtml(loan.borrower)}</td>
            <td>${escapeHtml(loan.department || "未填写")}</td>
            <td>${escapeHtml(loan.item_summary || loan.item_name || "未填写")}</td>
            <td>${formatDateTime(loan.loan_date, loan.loan_time)}</td>
            <td>${formatDateTime(loan.due_date, loan.due_time)}</td>
            <td>${isVenueLoan ? '<span class="pill venue-pill">场地借用</span>' : loanReturnStatus(loan)}</td>
            <td>${isVenueLoan ? "" : '<button class="inline-button" data-edit-loan="' + loan.id + '" type="button">修改</button>'}</td>
          </tr>
        `;
      },
    )
    .join("");
  renderPagination("#loansPagination", "loans", state.loans.length);
}

function renderViolationRecords() {
  if (state.violationRecords.length === 0) {
    $("#violationsBody").innerHTML = '<tr><td colspan="7" class="empty-cell">暂无违规记录</td></tr>';
    $("#violationsPagination").innerHTML = "";
    $("#selectAllViolations").checked = false;
    return;
  }

  const { start, end } = paginationInfo("violations", state.violationRecords.length);
  $("#selectAllViolations").checked = false;
  $("#violationsBody").innerHTML = state.violationRecords
    .slice(start, end)
    .map((record) => `
      <tr>
        <td class="check-cell">
          <label class="checkbox-container table-checkbox" title="选择违规记录">
            <input class="custom-checkbox" type="checkbox" data-violation-check value="${record.id}" aria-label="选择违规记录" />
            <span class="checkmark"></span>
          </label>
        </td>
        <td>${escapeHtml(record.borrower)}</td>
        <td>${escapeHtml(record.department || "未填写")}</td>
        <td>${escapeHtml(record.contact)}</td>
        <td>${escapeHtml(record.damaged_item)}</td>
        <td>${escapeHtml(record.resolution)}</td>
        <td>${escapeHtml(record.created_at || "")}</td>
      </tr>
    `)
    .join("");
  renderPagination("#violationsPagination", "violations", state.violationRecords.length);
}

function renderUsers() {
  if (!state.currentUser?.is_admin) return;
  if (state.users.length === 0) {
    $("#usersBody").innerHTML = '<tr><td colspan="7" class="empty-cell">暂无用户</td></tr>';
    return;
  }

  $("#usersBody").innerHTML = state.users
    .map((user) => {
      const isAdmin = Boolean(user.is_admin);
      const isPending = user.approval_status === "pending";
      return `
        <tr>
          <td>${escapeHtml(user.username)}</td>
          <td>${escapeHtml(user.display_name || "未填写")}</td>
          <td>${escapeHtml(user.phone || "未填写")}</td>
          <td><span class="pill ${isAdmin ? "warn" : ""}">${isAdmin ? "管理员" : "普通用户"}</span></td>
          <td><span class="pill ${isPending ? "warn" : ""}">${isPending ? "待审核" : "已通过"}</span></td>
          <td>${escapeHtml(user.created_at || "")}</td>
          <td>
            ${isPending ? `<button class="inline-button" type="button" data-approve-user="${user.id}">通过</button>` : ""}
            <button class="inline-button" type="button" data-edit-user="${user.id}" ${isAdmin ? "disabled" : ""}>修改</button>
            <button class="inline-button danger-inline" type="button" data-delete-user="${user.id}" ${isAdmin ? "disabled" : ""}>删除</button>
          </td>
        </tr>
      `;
    })
    .join("");
}

function currentRepositoryFolder() {
  return state.repositoryCurrentFolder || null;
}

function selectedRepositoryEntryRecord() {
  const selected = state.selectedRepositoryEntry;
  if (!selected) return null;
  const list = selected.type === "folder" ? state.repositoryFolders : state.repositoryDocuments;
  const record = list.find((item) => Number(item.id) === Number(selected.id));
  return record ? { ...selected, record } : null;
}

function selectRepositoryEntry(type, id) {
  state.selectedRepositoryEntry = { type, id };
  $$("#repositoryEntries [data-entry-type]").forEach((row) => {
    const isActive = row.dataset.entryType === type && Number(row.dataset.entryId) === Number(id);
    row.classList.toggle("active", isActive);
  });
}

function renderRepositoryBreadcrumbs() {
  const breadcrumbs = state.repositoryBreadcrumbs.length
    ? state.repositoryBreadcrumbs
    : state.repositoryCurrentFolder
      ? [state.repositoryCurrentFolder]
      : [];

  if (breadcrumbs.length === 0) {
    $("#repositoryBreadcrumb").innerHTML = '<span class="repository-path-empty">数据仓库</span>';
    return;
  }

  $("#repositoryBreadcrumb").innerHTML = breadcrumbs
    .map((folder, index) => `
      ${index > 0 ? '<span class="repository-breadcrumb-separator">/</span>' : ""}
      <button
        class="repository-breadcrumb-button"
        type="button"
        data-repository-breadcrumb="${folder.id}"
        ${index === breadcrumbs.length - 1 ? 'aria-current="page"' : ""}
      >
        ${escapeHtml(folder.name)}
      </button>
    `)
    .join("");
}

function renderRepositoryEntries() {
  const folders = state.repositoryFolders.map((folder) => ({
    type: "folder",
    id: folder.id,
    name: folder.name,
    kind: "文件夹",
    size: `${folder.folder_count || 0} 个文件夹 · ${folder.document_count || 0} 个文档`,
    createdAt: folder.created_at || "",
    record: folder,
  }));
  const documents = state.repositoryDocuments.map((document) => {
    const extension = fileExtension(document.original_name) || "文件";
    return {
      type: "document",
      id: document.id,
      name: document.original_name,
      kind: extension.toUpperCase(),
      size: formatFileSize(document.file_size),
      createdAt: document.created_at || "",
      record: document,
    };
  });
  const entries = [...folders, ...documents];

  $("#repositoryEntryCount").textContent = `${entries.length} 项`;
  if (!currentRepositoryFolder()) {
    $("#repositoryEntries").innerHTML = '<div class="empty-cell">数据仓库正在加载</div>';
    return;
  }

  if (entries.length === 0) {
    $("#repositoryEntries").innerHTML = '<div class="empty-cell">当前文件夹暂无内容</div>';
    return;
  }

  $("#repositoryEntries").innerHTML = entries
    .map((entry) => {
      const isActive = state.selectedRepositoryEntry
        && state.selectedRepositoryEntry.type === entry.type
        && Number(state.selectedRepositoryEntry.id) === Number(entry.id);
      return `
        <button
          class="repository-entry-row ${isActive ? "active" : ""}"
          type="button"
          data-entry-type="${entry.type}"
          data-entry-id="${entry.id}"
        >
          <span class="repository-entry-name">
            <span class="repository-entry-badge">${entry.type === "folder" ? "文件夹" : "文档"}</span>
            <strong>${escapeHtml(entry.name)}</strong>
          </span>
          <span>${escapeHtml(entry.kind)}</span>
          <span>${escapeHtml(entry.size)}</span>
          <span>${escapeHtml(entry.createdAt)}</span>
        </button>
      `;
    })
    .join("");
}

function renderRepository() {
  renderRepositoryBreadcrumbs();
  renderRepositoryEntries();
}

function buildVenueBookingMap() {
  const bookings = new Map();

  state.venueBookings
    .filter((booking) => booking.status === "Booked")
    .forEach((booking) => {
      bookings.set(`${booking.booking_date}|${booking.start_time}|${booking.end_time}`, booking);
    });

  return bookings;
}

function renderVenueDay(date, bookings, currentMonth = null) {
  const dateValue = formatDate(date);
  const isCurrentMonth = currentMonth === null || date.getMonth() === currentMonth;
  const dayClass = isCurrentMonth ? "" : "muted-day";
  const slots = VENUE_SLOTS.map((slot) => {
    const booking = bookings.get(`${dateValue}|${slot.start}|${slot.end}`);
    const unit = booking?.department || booking?.borrower || "";
    const safeUnit = escapeHtml(unit);
    const slotClass = booking ? "calendar-slot booked" : "calendar-slot";
    return `
      <button
        class="${slotClass}"
        data-venue-slot="${slot.value}"
        data-venue-date="${dateValue}"
        data-venue-unit="${safeUnit}"
        data-venue-booking-id="${booking?.id || ""}"
        type="button"
        aria-label="${dateValue} ${slot.label}"
      >
        <strong>${safeUnit}</strong>
      </button>
    `;
  }).join("");

  return `
    <article class="calendar-day ${dayClass}">
      <div class="calendar-date">${date.getDate()}</div>
      <div class="calendar-slots">${slots}</div>
    </article>
  `;
}

function renderVenueWeek(weekStartDate, bookings, currentMonth = null) {
  const days = Array.from({ length: 7 })
    .map((_, dayIndex) => {
      const date = new Date(
        weekStartDate.getFullYear(),
        weekStartDate.getMonth(),
        weekStartDate.getDate() + dayIndex,
      );
      return renderVenueDay(date, bookings, currentMonth);
    })
    .join("");

  return `
    <section class="calendar-week">
      <span class="calendar-axis-head">时间</span>
      <span class="weekday-label">一</span>
      <span class="weekday-label">二</span>
      <span class="weekday-label">三</span>
      <span class="weekday-label">四</span>
      <span class="weekday-label">五</span>
      <span class="weekday-label">六</span>
      <span class="weekday-label">日</span>
      <div class="calendar-time-axis">
        ${VENUE_SLOTS.map((slot) => `<span>${slot.label}</span>`).join("")}
      </div>
      ${days}
    </section>
  `;
}

function renderHomeVenueCalendar() {
  const bookings = buildVenueBookingMap();
  const weekStart = getWeekStart(new Date());
  const weekEnd = new Date(weekStart.getFullYear(), weekStart.getMonth(), weekStart.getDate() + 6);
  $("#homeWeekLabel").textContent = `${formatDate(weekStart)} 至 ${formatDate(weekEnd)}`;
  $("#homeVenueCalendar").innerHTML = renderVenueWeek(weekStart, bookings);
}

function renderVenueCalendar() {
  const monthDate = state.calendarDate;
  const year = monthDate.getFullYear();
  const month = monthDate.getMonth();
  const firstDay = new Date(year, month, 1);
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const leadingDays = (firstDay.getDay() + 6) % 7;
  const cellCount = Math.ceil((leadingDays + daysInMonth) / 7) * 7;
  const weekCount = cellCount / 7;
  const bookings = buildVenueBookingMap();

  $("#calendarMonthLabel").textContent = formatMonth(monthDate);
  $("#venueCalendar").innerHTML = Array.from({ length: weekCount })
    .map((_, weekIndex) => {
      const weekStart = new Date(year, month, 1 - leadingDays + weekIndex * 7);
      return renderVenueWeek(weekStart, bookings, month);
    })
    .join("");
}

function renderInventoryChart(snapshot, targets) {
  if (targets.dateLabel) {
    $(targets.dateLabel).textContent = snapshot.date;
  }

  const chart = $(targets.chart);
  state.inventoryChartSnapshots[targets.chart] = snapshot;
  state.inventoryChartTargets[targets.chart] = targets;

  const isExpanded = Boolean(state.inventoryChartExpanded[targets.chart]);
  const hiddenCount = Math.max(snapshot.items.length - CHART_COLLAPSED_LIMIT, 0);
  const visibleItems = isExpanded ? snapshot.items : snapshot.items.slice(0, CHART_COLLAPSED_LIMIT);
  const rows = visibleItems
    .map((item) => {
      const totalQuantity = Math.max(Number(item.total_quantity), 0);
      const availableQuantity = Math.max(Number(item.available_quantity), 0);
      const availableRatio = totalQuantity ? availableQuantity / totalQuantity : 0;
      const availablePercent = availableQuantity === 0 ? 0 : Math.max(availableRatio * 100, 3);
      const percentLabel = Math.round(availableRatio * 100);
      return `
        <div class="chart-row">
          <div class="chart-label">
            <strong>${escapeHtml(item.name)}</strong>
          </div>
          <div class="chart-current">
            <strong>${item.available_quantity}</strong>
            <span>${escapeHtml(item.unit)}</span>
          </div>
          <button
            class="bar-track"
            type="button"
            data-trend-item-id="${item.id}"
            data-trend-date="${snapshot.date}"
            aria-label="查看${escapeHtml(item.name)}从${snapshot.date}开始十天的剩余数量"
          >
            <div class="bar-fill" style="width: ${availablePercent}%"></div>
            <span class="bar-track-label">${percentLabel}%</span>
          </button>
        </div>
      `;
    })
    .join("");
  const toggle = hiddenCount
    ? `
      <div class="chart-toggle-row">
        <button class="chart-toggle-button ghost-button" type="button" data-chart-toggle="${targets.chart}">
          ${isExpanded ? "收起" : "展开"}
        </button>
      </div>
    `
    : "";

  chart.dataset.snapshotDate = snapshot.date;
  chart.innerHTML = rows + toggle;
}

async function loadInventorySnapshot(dateValue, targets) {
  const snapshot = await api(`/api/inventory-snapshot?date=${encodeURIComponent(dateValue)}`);
  renderInventoryChart(snapshot, targets);
}

async function loadHomeInventorySnapshot() {
  await loadInventorySnapshot(today(), {
    chart: "#homeInventoryChart",
    dateLabel: "#homeInventoryDate",
  });
}

async function loadInventoryPageSnapshot(dateValue = $("#inventorySnapshotDate").value || today()) {
  await loadInventorySnapshot(dateValue, {
    chart: "#inventoryPageChart",
  });
}

async function loadRepository(folderId = state.activeRepositoryFolderId) {
  const query = folderId ? `?folder_id=${encodeURIComponent(folderId)}` : "";
  const data = await api(`/api/repository${query}`);
  state.repositoryRootFolderId = data.root_id || null;
  state.repositoryCurrentFolder = data.current_folder || null;
  state.repositoryBreadcrumbs = data.breadcrumbs || [];
  state.activeRepositoryFolderId = data.current_folder?.id || null;
  state.repositoryFolders = data.folders || [];
  state.repositoryDocuments = data.documents || [];
  state.selectedRepositoryEntry = null;
  renderRepository();
}

async function loadCurrentUser() {
  const data = await api("/api/me");
  state.currentUser = data.user || null;
  $("#currentAccountLabel").textContent = state.currentUser?.username || "未登录";
  configureAdminNavigation();
}

async function loadUsers() {
  if (!state.currentUser?.is_admin) return;
  const data = await api("/api/users");
  state.users = data.users || [];
  renderUsers();
}

async function loadDashboard() {
  const data = await api("/api/dashboard");
  state.items = data.items;
  state.loans = data.loans;
  state.venueBookings = data.venue_bookings || [];
  state.violationRecords = data.violation_records || [];

  renderStats(data.stats);
  renderLoanMaterialControls();
  renderItems();
  renderLoans();
  renderViolationRecords();
  renderHomeVenueCalendar();
  renderVenueCalendar();
  await Promise.all([loadHomeInventorySnapshot(), loadInventoryPageSnapshot(), loadRepository(), loadUsers()]);
}

async function submitJson(form, path, successMessage) {
  const payload = formPayload(form);
  await api(path, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  form.reset();
  setDefaultDates();
  await loadDashboard();
  showToast(successMessage);
}

function setDefaultDates() {
  const loanDate = document.querySelector('input[name="loan_date"]');
  const dueDate = document.querySelector('input[name="due_date"]');
  const inventorySnapshotDate = $("#inventorySnapshotDate");
  const bookingDate = document.querySelector('input[name="booking_date"]');

  if (loanDate && !loanDate.value) loanDate.value = today();
  if (dueDate && !dueDate.value) dueDate.value = today();
  if (inventorySnapshotDate && !inventorySnapshotDate.value) inventorySnapshotDate.value = today();
  if (bookingDate && !bookingDate.value) bookingDate.value = today();
}

function openLoanModal(loan = null) {
  const form = $("#loanForm");
  form.reset();
  renderLoanMaterialControls(loan);

  $("#loanModalTitle").textContent = loan ? "修改借出记录" : "新增借出记录";
  form.elements.id.value = loan?.id || "";
  form.elements.borrower.value = loan?.borrower || "";
  form.elements.department.value = loan?.department || "";
  form.elements.contact.value = loan?.contact || "";
  form.elements.purpose.value = loan?.purpose || "";
  form.elements.custom_item_name.value = loan?.custom_item_name || "";
  form.elements.custom_item_quantity.value = loan?.custom_item_quantity || 0;
  form.elements.loan_date.value = loan?.loan_date || today();
  form.elements.due_date.value = loan?.due_date || today();
  setRadioValue(form, "loan_time", loan?.loan_time);
  setRadioValue(form, "due_time", loan?.due_time);

  $("#loanModal").hidden = false;
  document.body.classList.add("modal-open");
}

function closeLoanModal() {
  $("#loanModal").hidden = true;
  document.body.classList.remove("modal-open");
}

function openItemModal(item = null) {
  const form = $("#itemForm");
  const isEdit = Boolean(item);
  form.reset();

  $("#itemModalTitle").textContent = isEdit ? "修改物资" : "新增物资";
  form.elements.id.value = item?.id || "";
  form.elements.name.value = item?.name || "";
  form.elements.size.value = item?.size || "无";
  form.elements.total_quantity.value = item?.total_quantity ?? "";
  form.elements.unit.value = item?.unit || "";

  ["name", "unit"].forEach((fieldName) => {
    form.elements[fieldName].readOnly = isEdit;
  });

  $("#itemModal").hidden = false;
  document.body.classList.add("modal-open");
  form.elements.total_quantity.focus();
}

function closeItemModal() {
  $("#itemModal").hidden = true;
  document.body.classList.remove("modal-open");
}

function renderItemTrendChart(data) {
  const item = data.item;
  const unit = item.unit || "";
  const maxQuantity = Math.max(
    Number(item.total_quantity) || 0,
    ...data.days.map((day) => Number(day.available_quantity) || 0),
    1,
  );

  $("#trendModalTitle").textContent = `${item.name}十日剩余数量`;
  $("#trendModalRange").textContent = `${data.start_date} 至 ${data.end_date}，单位：${unit}`;
  $("#itemTrendChart").innerHTML = `
    <div class="trend-y-scale">
      <span>${maxQuantity}</span>
      <span>${Math.round(maxQuantity / 2)}</span>
      <span>0</span>
    </div>
    <div class="trend-bars">
      ${data.days
        .map((day) => {
          const availableQuantity = Math.max(Number(day.available_quantity) || 0, 0);
          const height = availableQuantity === 0 ? 0 : Math.max((availableQuantity / maxQuantity) * 100, 4);
          return `
            <div class="trend-bar-column">
              <span class="trend-value">${availableQuantity}</span>
              <div class="trend-bar-track">
                <div class="trend-bar" style="height: ${height}%"></div>
              </div>
              <span class="trend-date">${formatShortDate(day.date)}</span>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

async function openTrendModal(itemId, startDate) {
  $("#trendModalTitle").textContent = "十日剩余数量";
  $("#trendModalRange").textContent = "加载中";
  $("#itemTrendChart").innerHTML = '<div class="trend-loading">正在加载数据</div>';
  $("#trendModal").hidden = false;
  document.body.classList.add("modal-open");

  const data = await api(
    `/api/item-trend?item_id=${encodeURIComponent(itemId)}&start_date=${encodeURIComponent(startDate)}`,
  );
  renderItemTrendChart(data);
}

function closeTrendModal() {
  $("#trendModal").hidden = true;
  document.body.classList.remove("modal-open");
}

function openVenueModal(defaults = {}) {
  const form = $("#venueBookingForm");
  const isEditing = Boolean(defaults.id);
  form.reset();
  $("#venueModalTitle").textContent = isEditing ? "修改场地借用" : "新增场地借用";
  $("#deleteVenueModalButton").hidden = !isEditing;
  form.elements.id.value = defaults.id || "";
  form.elements.department.value = defaults.department || "";
  form.elements.borrower.value = defaults.borrower || "";
  form.elements.contact.value = defaults.contact || "";
  form.elements.purpose.value = defaults.purpose || "";
  form.elements.booking_date.value = defaults.booking_date || defaults.date || today();
  form.elements.setup_time.value = defaults.setup_time || "";
  form.elements.estimated_attendance.value = defaults.estimated_attendance || "";
  form.elements.folding_table_quantity.value = defaults.folding_table_quantity || 0;
  form.elements.plastic_chair_quantity.value = defaults.plastic_chair_quantity || 0;
  const selectedSlot = defaults.id ? `${defaults.start_time}|${defaults.end_time}` : (defaults.slot || VENUE_SLOTS[0].value);
  form.querySelectorAll('input[name="time_slots"]').forEach((input) => {
    input.checked = input.value === selectedSlot;
    input.disabled = isEditing && input.value !== selectedSlot;
  });

  $("#venueModal").hidden = false;
  document.body.classList.add("modal-open");
}

function closeVenueModal() {
  $("#venueModal").hidden = true;
  document.body.classList.remove("modal-open");
  $("#venueBookingForm").querySelectorAll('input[name="time_slots"]').forEach((input) => {
    input.disabled = false;
  });
}

function openViolationModal() {
  const form = $("#violationForm");
  form.reset();
  $("#violationModal").hidden = false;
  document.body.classList.add("modal-open");
}

function closeViolationModal() {
  $("#violationModal").hidden = true;
  document.body.classList.remove("modal-open");
}

function openUserModal(user) {
  const form = $("#userForm");
  form.reset();
  form.elements.id.value = user.id;
  form.elements.display_name.value = user.display_name || "";
  form.elements.student_id.value = user.student_id || "";
  form.elements.phone.value = user.phone || "";
  $("#userModal").hidden = false;
  document.body.classList.add("modal-open");
  form.elements.student_id.focus();
}

function closeUserModal() {
  $("#userModal").hidden = true;
  document.body.classList.remove("modal-open");
}

function openRepositoryFolderModal() {
  const form = $("#repositoryFolderForm");
  form.reset();
  $("#repositoryFolderModal").hidden = false;
  document.body.classList.add("modal-open");
  form.elements.name.focus();
}

function closeRepositoryFolderModal() {
  $("#repositoryFolderModal").hidden = true;
  document.body.classList.remove("modal-open");
}

function closeDocumentPreviewModal() {
  $("#documentPreviewModal").hidden = true;
  $("#documentPreviewContent").innerHTML = "";
  state.activeRepositoryDocumentId = null;
  document.body.classList.remove("modal-open");
}

function handleTablePagination(event) {
  const button = event.target.closest("[data-page-number]");
  if (!button || button.disabled) return;

  const key = button.dataset.pageKey;
  state.pagination[key] = Number(button.dataset.pageNumber);

  if (key === "loans") {
    renderLoans();
    return;
  }

  if (key === "violations") {
    renderViolationRecords();
    return;
  }

}

async function openDocumentPreview(documentId) {
  const documentRecord = state.repositoryDocuments.find((item) => Number(item.id) === Number(documentId));
  if (!documentRecord) return;

  state.activeRepositoryDocumentId = documentRecord.id;
  const type = documentPreviewType(documentRecord);
  const fileUrl = `/api/repository-documents/${documentRecord.id}/file`;

  $("#documentPreviewTitle").textContent = documentRecord.original_name;
  $("#documentPreviewMeta").textContent = `${documentRecord.folder_name || "数据仓库"} · ${formatFileSize(documentRecord.file_size)}`;
  $("#downloadPreviewDocumentButton").href = `${fileUrl}?download=1`;
  $("#documentPreviewContent").innerHTML = '<div class="document-preview-empty"><strong>正在加载预览</strong></div>';
  $("#documentPreviewModal").hidden = false;
  document.body.classList.add("modal-open");

  if (type === "image") {
    $("#documentPreviewContent").innerHTML = `<img src="${fileUrl}" alt="${escapeHtml(documentRecord.original_name)}" />`;
    return;
  }

  if (type === "pdf") {
    $("#documentPreviewContent").innerHTML = `<iframe src="${fileUrl}" title="${escapeHtml(documentRecord.original_name)}"></iframe>`;
    return;
  }

  if (type === "text") {
    try {
      const response = await fetch(fileUrl);
      const text = await response.text();
      if (!response.ok) throw new Error(text || "文档读取失败");
      $("#documentPreviewContent").innerHTML = `<pre>${escapeHtml(text)}</pre>`;
    } catch (error) {
      $("#documentPreviewContent").innerHTML = `
        <div class="document-preview-empty">
          <strong>预览失败</strong>
          <span>${escapeHtml(error.message)}</span>
        </div>
      `;
    }
    return;
  }

  const message = type === "office"
    ? "Office 文件第一版暂不支持在线预览，可以先下载查看。"
    : "这个文件类型暂不支持在线预览，可以下载查看。";
  $("#documentPreviewContent").innerHTML = `
    <div class="document-preview-empty">
      <strong>暂不支持在线预览</strong>
      <span>${message}</span>
    </div>
  `;
}

function selectedLoanIds() {
  return $$("[data-loan-check]:checked").map((checkbox) => checkbox.value);
}

function selectedViolationRecordIds() {
  return $$("[data-violation-check]:checked").map((checkbox) => checkbox.value);
}

async function deleteSelectedLoans() {
  const ids = selectedLoanIds();
  if (ids.length === 0) {
    showToast("请先选择要删除的借出记录");
    return;
  }

  const confirmed = await openConfirmModal(`确定删除选中的 ${ids.length} 条借出记录吗？`);
  if (!confirmed) return;

  await Promise.all(ids.map((id) => api(`/api/loans/${id}`, { method: "DELETE" })));
  $("#selectAllLoans").checked = false;
  await loadDashboard();
  showToast("借出记录已删除");
}

async function deleteSelectedViolationRecords() {
  const ids = selectedViolationRecordIds();
  if (ids.length === 0) {
    showToast("请先选择要删除的违规记录");
    return;
  }

  const confirmed = await openConfirmModal(`确定删除选中的 ${ids.length} 条违规记录吗？`);
  if (!confirmed) return;

  await Promise.all(ids.map((id) => api(`/api/violation-records/${id}`, { method: "DELETE" })));
  $("#selectAllViolations").checked = false;
  await loadDashboard();
  showToast("违规记录已删除");
}

async function saveLoan(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = formPayload(form);
  const loanId = payload.id;
  delete payload.id;
  delete payload.item_id;
  delete payload.quantity;

  if (!/^\d{11}$/.test(payload.contact || "")) {
    showToast("手机号必须是 11 位数字");
    return;
  }

  let loanItems = [];
  try {
    loanItems = collectLoanItems();
  } catch (error) {
    showToast(error.message);
    return;
  }

  const customName = String(payload.custom_item_name || "").trim();
  const customQuantity = Number(payload.custom_item_quantity || 0);
  if (customQuantity > 0 && !customName) {
    showToast("请填写手动其他物资名称");
    return;
  }
  if (customName && customQuantity <= 0) {
    showToast("请填写手动其他数量");
    return;
  }
  if (loanItems.length === 0 && customQuantity <= 0) {
    showToast("请至少填写一种借用物资");
    return;
  }
  payload.loan_items = loanItems;

  await api(loanId ? `/api/loans/${loanId}` : "/api/loans", {
    method: loanId ? "PUT" : "POST",
    body: JSON.stringify(payload),
  });

  state.pagination.loans = 1;
  closeLoanModal();
  await loadDashboard();
  openSuccessModal("保存成功，请提醒办理人正确的物资借还时间");
}

async function saveItem(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = formPayload(form);
  const itemId = payload.id;
  delete payload.id;

  await api(itemId ? `/api/items/${itemId}` : "/api/items", {
    method: itemId ? "PUT" : "POST",
    body: JSON.stringify(payload),
  });

  closeItemModal();
  form.reset();
  await loadDashboard();
  showToast(itemId ? "物资总数量已修改" : "物资添加成功");
}

async function saveVenueBooking(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = formPayload(form);
  const bookingId = payload.id;
  delete payload.id;

  if (!/^\d{11}$/.test(payload.contact || "")) {
    showToast("手机号必须是 11 位数字");
    return;
  }

  const timeSlots = Array.from(form.querySelectorAll('input[name="time_slots"]:checked')).map((input) => input.value);
  if (timeSlots.length === 0) {
    showToast("请至少选择一个时间段");
    return;
  }
  payload.time_slots = timeSlots;

  await api(bookingId ? `/api/venue-bookings/${bookingId}` : "/api/venue-bookings", {
    method: bookingId ? "PUT" : "POST",
    body: JSON.stringify(payload),
  });

  closeVenueModal();
  form.reset();
  setDefaultDates();
  await loadDashboard();
  openSuccessModal("保存成功，请提醒办理人活动结束后做好卫生");
}

async function saveViolationRecord(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = formPayload(form);

  if (!/^\d{11}$/.test(payload.contact || "")) {
    showToast("手机号必须是 11 位数字");
    return;
  }

  await api("/api/violation-records", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  closeViolationModal();
  form.reset();
  state.pagination.violations = 1;
  await loadDashboard();
  showToast("违规记录已保存");
}

async function saveUser(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = formPayload(form);
  const userId = payload.id;
  delete payload.id;

  if (!String(payload.display_name || "").trim()) {
    showToast("请填写姓名");
    return;
  }
  if (!/^\d{10}$/.test(payload.student_id || "")) {
    showToast("学号必须是 10 位数字");
    return;
  }
  if (!/^\d{11}$/.test(payload.phone || "")) {
    showToast("手机号必须是 11 位数字");
    return;
  }
  if (payload.password && payload.password.length < 6) {
    showToast("密码至少需要 6 位");
    return;
  }

  await api(`/api/users/${userId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  closeUserModal();
  await loadUsers();
  showToast("用户信息已修改");
}

async function deleteUserRecord(userId) {
  const user = state.users.find((item) => Number(item.id) === Number(userId));
  if (!user) return;
  const confirmed = await openConfirmModal(`确定删除用户“${user.username}”吗？`);
  if (!confirmed) return;

  await api(`/api/users/${user.id}`, { method: "DELETE" });
  await loadUsers();
  showToast("用户已删除");
}

async function approveUserRecord(userId) {
  const user = state.users.find((item) => Number(item.id) === Number(userId));
  if (!user) return;

  await api(`/api/users/${user.id}/approve`, { method: "POST" });
  await loadUsers();
  showToast(`已通过 ${user.display_name || user.username} 的注册申请`);
}

async function saveRepositoryFolder(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const parentId = state.activeRepositoryFolderId;
  const folder = await api("/api/repository-folders", {
    method: "POST",
    body: JSON.stringify({
      ...formPayload(form),
      parent_id: parentId,
    }),
  });
  closeRepositoryFolderModal();
  await loadRepository(parentId);
  state.selectedRepositoryEntry = { type: "folder", id: folder.id };
  renderRepositoryEntries();
  showToast("文件夹已新建");
}

async function openRepositoryEntry(entry) {
  if (entry.type === "folder") {
    await loadRepository(entry.id);
    return;
  }

  await openDocumentPreview(entry.id);
}

async function deleteSelectedRepositoryEntry() {
  const selected = selectedRepositoryEntryRecord();
  if (!selected) {
    showToast("请先选择要删除的文件夹或文档");
    return;
  }

  if (selected.type === "document") {
    await deleteRepositoryDocument(selected.id);
    return;
  }

  const confirmed = await openConfirmModal(`确定删除文件夹“${selected.record.name}”吗？`);
  if (!confirmed) return;

  await api(`/api/repository-folders/${selected.record.id}`, { method: "DELETE" });
  await loadRepository(state.activeRepositoryFolderId);
  showToast("文件夹已删除");
}

async function uploadSingleDocument(file) {
  const folder = currentRepositoryFolder();
  if (!folder) throw new Error("数据仓库正在加载，请稍后再试");

  const formData = new FormData();
  formData.append("folder_id", folder.id);
  formData.append("file", file);

  const response = await fetch("/api/repository-documents", {
    method: "POST",
    body: formData,
  });
  const data = await response.json();
  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error(data.error || "请先登录。");
  }
  if (!response.ok) {
    throw new Error(data.error || "上传失败");
  }
  return data;
}

async function uploadRepositoryDocuments(event) {
  const files = Array.from(event.currentTarget.files || []);
  event.currentTarget.value = "";
  if (files.length === 0) return;

  try {
    for (const file of files) {
      await uploadSingleDocument(file);
    }
    await loadRepository();
    showToast(files.length === 1 ? "文档已上传" : `${files.length} 个文档已上传`);
  } catch (error) {
    await loadRepository();
    showToast(error.message);
  }
}

async function deleteRepositoryDocument(documentId) {
  const documentRecord = state.repositoryDocuments.find((item) => Number(item.id) === Number(documentId));
  if (!documentRecord) return;
  const confirmed = await openConfirmModal(`确定删除文档“${documentRecord.original_name}”吗？`);
  if (!confirmed) return;

  await api(`/api/repository-documents/${documentRecord.id}`, { method: "DELETE" });
  if (Number(state.activeRepositoryDocumentId) === Number(documentRecord.id)) {
    closeDocumentPreviewModal();
  }
  await loadRepository();
  showToast("文档已删除");
}

async function deleteCurrentVenueBooking() {
  const bookingId = $("#venueBookingForm").elements.id.value;
  if (!bookingId) return;
  const confirmed = await openConfirmModal("确定删除这条场地借用记录吗？相关桌椅占用也会一起删除。");
  if (!confirmed) return;

  await api(`/api/venue-bookings/${bookingId}`, { method: "DELETE" });
  closeVenueModal();
  await loadDashboard();
  showToast("场地借用已删除");
}

async function logout() {
  await api("/api/logout", { method: "POST" });
  window.location.href = "/login";
}

function bindEvents() {
  $$('input[name="mainNav"]').forEach((input) => {
    input.addEventListener("change", () => {
      if (input.checked) setActiveView(input.dataset.viewTarget);
    });
  });

  $("#inventorySnapshotDate").addEventListener("change", async (event) => {
    try {
      await loadInventoryPageSnapshot(event.currentTarget.value);
      showToast("统计图已更新");
    } catch (error) {
      showToast(error.message);
    }
  });

  $$("input[data-date-picker]").forEach((input) => {
    input.addEventListener("click", () => openDatePicker(input));
    input.addEventListener("focus", () => openDatePicker(input));
  });

  $("#customDatePicker").addEventListener("click", (event) => {
    event.stopPropagation();

    const navButton = event.target.closest("[data-date-nav]");
    if (navButton) {
      const offset = Number(navButton.dataset.dateNav);
      state.datePickerMonth = new Date(
        state.datePickerMonth.getFullYear(),
        state.datePickerMonth.getMonth() + offset,
        1,
      );
      renderDatePicker();
      return;
    }

    const dayButton = event.target.closest("[data-date-value]");
    if (dayButton) {
      setPickedDate(dayButton.dataset.dateValue);
      return;
    }

    if (event.target.closest("[data-date-clear]")) {
      setPickedDate(today());
      return;
    }

    if (event.target.closest("[data-date-today]")) {
      setPickedDate(today());
    }
  });

  document.addEventListener("click", (event) => {
    if (event.target.closest("input[data-date-picker]") || event.target.closest("#customDatePicker")) return;
    closeDatePicker();
  });

  window.addEventListener("resize", closeDatePicker);
  window.addEventListener("scroll", closeDatePicker, true);

  $("#logoutButton").addEventListener("click", () => {
    logout().catch((error) => showToast(error.message));
  });

  $("#themeToggleButton").addEventListener("click", toggleMatrixTheme);
  $("#confirmSuccessModalButton").addEventListener("click", closeSuccessModal);
  $("#successModal").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeSuccessModal();
  });
  $("#cancelConfirmModalButton").addEventListener("click", () => closeConfirmModal(false));
  $("#acceptConfirmModalButton").addEventListener("click", () => closeConfirmModal(true));
  $("#confirmModal").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeConfirmModal(false);
  });

  ["#homeInventoryChart", "#inventoryPageChart"].forEach((selector) => {
    $(selector).addEventListener("click", (event) => {
      const toggle = event.target.closest("[data-chart-toggle]");
      if (toggle) {
        const chartSelector = toggle.dataset.chartToggle;
        state.inventoryChartExpanded[chartSelector] = !state.inventoryChartExpanded[chartSelector];
        renderInventoryChart(state.inventoryChartSnapshots[chartSelector], state.inventoryChartTargets[chartSelector]);
        return;
      }

      const button = event.target.closest("[data-trend-item-id]");
      if (!button) return;
      openTrendModal(button.dataset.trendItemId, button.dataset.trendDate).catch((error) => {
        closeTrendModal();
        showToast(error.message);
      });
    });
  });
  $("#closeTrendModalButton").addEventListener("click", closeTrendModal);
  $("#trendModal").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeTrendModal();
  });

  $("#addItemButton").addEventListener("click", () => openItemModal());
  $("#closeItemModalButton").addEventListener("click", closeItemModal);
  $("#cancelItemModalButton").addEventListener("click", closeItemModal);
  $("#itemModal").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeItemModal();
  });
  $("#itemForm").addEventListener("submit", (event) => {
    saveItem(event).catch((error) => showToast(error.message));
  });
  $("#itemsBody").addEventListener("click", (event) => {
    const button = event.target.closest("[data-edit-item]");
    if (!button) return;

    const item = state.items.find((entry) => Number(entry.id) === Number(button.dataset.editItem));
    if (item) openItemModal(item);
  });

  $("#addLoanButton").addEventListener("click", () => openLoanModal());
  $("#deleteLoanButton").addEventListener("click", () => {
    deleteSelectedLoans().catch((error) => showToast(error.message));
  });
  $("#cancelLoanModalButton").addEventListener("click", closeLoanModal);
  document.querySelector('#loanForm input[name="contact"]').addEventListener("input", (event) => {
    event.currentTarget.value = event.currentTarget.value.replace(/\D/g, "").slice(0, 11);
  });
  $("#loanModal").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeLoanModal();
  });

  $("#loanForm").addEventListener("submit", (event) => {
    saveLoan(event).catch((error) => showToast(error.message));
  });

  $("#prevMonthButton").addEventListener("click", () => {
    state.calendarDate = new Date(state.calendarDate.getFullYear(), state.calendarDate.getMonth() - 1, 1);
    renderVenueCalendar();
  });

  $("#nextMonthButton").addEventListener("click", () => {
    state.calendarDate = new Date(state.calendarDate.getFullYear(), state.calendarDate.getMonth() + 1, 1);
    renderVenueCalendar();
  });

  $("#addVenueBookingButton").addEventListener("click", () => openVenueModal());
  $("#cancelVenueModalButton").addEventListener("click", closeVenueModal);
  $("#deleteVenueModalButton").addEventListener("click", () => {
    deleteCurrentVenueBooking().catch((error) => showToast(error.message));
  });
  document.querySelector('#venueBookingForm input[name="contact"]').addEventListener("input", (event) => {
    event.currentTarget.value = event.currentTarget.value.replace(/\D/g, "").slice(0, 11);
  });
  $("#venueModal").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeVenueModal();
  });

  $("#venueCalendar").addEventListener("click", (event) => {
    const button = event.target.closest("[data-venue-slot]");
    if (!button) return;
    if (button.dataset.venueBookingId) {
      const booking = state.venueBookings.find((item) => Number(item.id) === Number(button.dataset.venueBookingId));
      if (booking) openVenueModal(booking);
      return;
    }
    openVenueModal({
      date: button.dataset.venueDate,
      slot: button.dataset.venueSlot,
    });
  });

  $("#homeVenueCalendar").addEventListener("click", (event) => {
    const button = event.target.closest("[data-venue-slot]");
    if (!button?.dataset.venueBookingId) return;
    const booking = state.venueBookings.find((item) => Number(item.id) === Number(button.dataset.venueBookingId));
    if (booking) openVenueModal(booking);
  });

  $("#selectAllLoans").addEventListener("change", (event) => {
    $$("[data-loan-check]").forEach((checkbox) => {
      checkbox.checked = event.currentTarget.checked;
    });
  });
  $("#selectAllViolations").addEventListener("change", (event) => {
    $$("[data-violation-check]").forEach((checkbox) => {
      checkbox.checked = event.currentTarget.checked;
    });
  });
  $("#loansPagination").addEventListener("click", handleTablePagination);
  $("#violationsPagination").addEventListener("click", handleTablePagination);

  $("#loansBody").addEventListener("click", (event) => {
    const button = event.target.closest("[data-edit-loan]");
    if (!button) return;

    const loan = state.loans.find((item) => Number(item.id) === Number(button.dataset.editLoan));
    if (loan) openLoanModal(loan);
  });

  $("#venueBookingForm").addEventListener("submit", (event) => {
    saveVenueBooking(event).catch((error) => showToast(error.message));
  });

  $("#addViolationButton").addEventListener("click", openViolationModal);
  $("#deleteViolationButton").addEventListener("click", () => {
    deleteSelectedViolationRecords().catch((error) => showToast(error.message));
  });
  $("#cancelViolationModalButton").addEventListener("click", closeViolationModal);
  document.querySelector('#violationForm input[name="contact"]').addEventListener("input", (event) => {
    event.currentTarget.value = event.currentTarget.value.replace(/\D/g, "").slice(0, 11);
  });
  $("#violationModal").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeViolationModal();
  });
  $("#violationForm").addEventListener("submit", (event) => {
    saveViolationRecord(event).catch((error) => showToast(error.message));
  });

  $("#cancelUserModalButton").addEventListener("click", closeUserModal);
  $("#userModal").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeUserModal();
  });
  $("#userForm").addEventListener("submit", (event) => {
    saveUser(event).catch((error) => showToast(error.message));
  });
  $("#userForm").querySelector('input[name="student_id"]').addEventListener("input", (event) => {
    event.currentTarget.value = event.currentTarget.value.replace(/\D/g, "").slice(0, 10);
  });
  $("#userForm").querySelector('input[name="phone"]').addEventListener("input", (event) => {
    event.currentTarget.value = event.currentTarget.value.replace(/\D/g, "").slice(0, 11);
  });
  $("#usersBody").addEventListener("click", (event) => {
    const approveButton = event.target.closest("[data-approve-user]");
    if (approveButton) {
      approveUserRecord(approveButton.dataset.approveUser).catch((error) => showToast(error.message));
      return;
    }

    const editButton = event.target.closest("[data-edit-user]");
    if (editButton && !editButton.disabled) {
      const user = state.users.find((item) => Number(item.id) === Number(editButton.dataset.editUser));
      if (user) openUserModal(user);
      return;
    }

    const deleteButton = event.target.closest("[data-delete-user]");
    if (deleteButton && !deleteButton.disabled) {
      deleteUserRecord(deleteButton.dataset.deleteUser).catch((error) => showToast(error.message));
    }
  });

  $("#addRepositoryFolderButton").addEventListener("click", openRepositoryFolderModal);
  $("#deleteRepositoryFolderButton").addEventListener("click", () => {
    deleteSelectedRepositoryEntry().catch((error) => showToast(error.message));
  });
  $("#cancelRepositoryFolderButton").addEventListener("click", closeRepositoryFolderModal);
  $("#repositoryFolderModal").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeRepositoryFolderModal();
  });
  $("#repositoryFolderForm").addEventListener("submit", (event) => {
    saveRepositoryFolder(event).catch((error) => showToast(error.message));
  });
  $("#uploadDocumentButton").addEventListener("click", () => {
    if (!currentRepositoryFolder()) {
      showToast("数据仓库正在加载，请稍后再试");
      return;
    }
    $("#documentUploadInput").click();
  });
  $("#documentUploadInput").addEventListener("change", (event) => {
    uploadRepositoryDocuments(event).catch((error) => showToast(error.message));
  });
  $("#repositoryBreadcrumb").addEventListener("click", (event) => {
    const button = event.target.closest("[data-repository-breadcrumb]");
    if (!button) return;
    loadRepository(button.dataset.repositoryBreadcrumb).catch((error) => showToast(error.message));
  });
  $("#repositoryEntries").addEventListener("click", (event) => {
    const row = event.target.closest("[data-entry-type]");
    if (!row) return;
    selectRepositoryEntry(row.dataset.entryType, row.dataset.entryId);
  });
  $("#repositoryEntries").addEventListener("dblclick", (event) => {
    const row = event.target.closest("[data-entry-type]");
    if (!row) return;
    openRepositoryEntry({
      type: row.dataset.entryType,
      id: row.dataset.entryId,
    }).catch((error) => showToast(error.message));
  });
  $("#repositoryEntries").addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    const row = event.target.closest("[data-entry-type]");
    if (!row) return;
    openRepositoryEntry({
      type: row.dataset.entryType,
      id: row.dataset.entryId,
    }).catch((error) => showToast(error.message));
  });
  $("#closeDocumentPreviewButton").addEventListener("click", closeDocumentPreviewModal);
  $("#documentPreviewModal").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeDocumentPreviewModal();
  });
  $("#deletePreviewDocumentButton").addEventListener("click", () => {
    if (!state.activeRepositoryDocumentId) return;
    deleteRepositoryDocument(state.activeRepositoryDocumentId).catch((error) => showToast(error.message));
  });
}

setMatrixTheme(getSavedMatrixTheme());
renderMatrixBackground();
setDefaultDates();
bindEvents();

async function initialize() {
  await loadCurrentUser();
  await loadDashboard();
}

initialize().catch((error) => showToast(error.message));
