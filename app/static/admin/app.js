document.addEventListener('DOMContentLoaded', () => {
  // ==========================================
  // 1. GLOBAL STATE & FIFO CACHE MANAGER
  // ==========================================
  let calendar = null;
  let selectedUser = null; // Currently selected user for Calendar view
  const checkedInDates = new Set();
  
  // Abort Controllers for Non-Blocking Async Requests
  let searchAbortController = null;
  let calendarFetchController = null;
  let empTableFetchController = null;
  let lastSearchResults = [];

  // FIFO Cache Manager Class (Max capacity: 20 employees)
  class FIFOCacheManager {
    constructor(maxCapacity = 20) {
      this.maxCapacity = maxCapacity;
      this.cacheMap = new Map();
    }

    get(key) {
      return this.cacheMap.get(key);
    }

    has(key) {
      return this.cacheMap.has(key);
    }

    set(key, value) {
      if (this.cacheMap.has(key)) {
        this.cacheMap.delete(key);
      } else if (this.cacheMap.size >= this.maxCapacity) {
        const oldestKey = this.cacheMap.keys().next().value;
        this.cacheMap.delete(oldestKey);
        console.log(`[FIFO Cache] Evicted oldest entry: ${oldestKey}`);
      }
      this.cacheMap.set(key, value);
    }

    clear() {
      this.cacheMap.clear();
    }
  }

  const employeeCache = new FIFOCacheManager(20);

  // Table State
  let sortColumn = 'employeeCode';
  let sortOrder = 'ASC';
  let isBulkDeleteMode = false;
  let bulkSelectedIds = new Set();
  let pendingDeleteAction = null;
  let currentEmployeesList = [];

  // ==========================================
  // 2. DOM ELEMENTS SELECTION
  // ==========================================
  // SPA Tabs
  const tabBtnCalendar = document.getElementById('tabBtnCalendar');
  const tabBtnEmployees = document.getElementById('tabBtnEmployees');
  const calendarTab = document.getElementById('calendarTab');
  const employeesTab = document.getElementById('employeesTab');

  // Calendar Controls
  const userSearchInput = document.getElementById('userSearchInput');
  const clearSearchBtn = document.getElementById('clearSearchBtn');
  const searchSuggestions = document.getElementById('searchSuggestions');
  const jumpDatePicker = document.getElementById('jumpDatePicker');
  const selectedUserStrip = document.getElementById('selectedUserStrip');
  const selectedName = document.getElementById('selectedName');
  const selectedCode = document.getElementById('selectedCode');
  const selectedGender = document.getElementById('selectedGender');
  const selectedDob = document.getElementById('selectedDob');
  const deselectUserBtn = document.getElementById('deselectUserBtn');

  // Employee Toolbar
  const standardActionBar = document.getElementById('standardActionBar');
  const bulkActionBar = document.getElementById('bulkActionBar');
  const btnAddEmployee = document.getElementById('btnAddEmployee');
  const btnEditEmployee = document.getElementById('btnEditEmployee');
  const btnBulkDeleteMode = document.getElementById('btnBulkDeleteMode');
  const btnCancelBulk = document.getElementById('btnCancelBulk');
  const btnConfirmBulkDelete = document.getElementById('btnConfirmBulkDelete');
  const bulkSelectCount = document.getElementById('bulkSelectCount');

  // Employee Filters
  const empSearchInput = document.getElementById('empSearchInput');
  const empDateFilterMode = document.getElementById('empDateFilterMode');
  const empExactDatePicker = document.getElementById('empExactDatePicker');
  const empStartDatePicker = document.getElementById('empStartDatePicker');
  const empEndDatePicker = document.getElementById('empEndDatePicker');
  const rangeSeparator = document.getElementById('rangeSeparator');
  const btnClearEmpFilters = document.getElementById('btnClearEmpFilters');

  // Employee Table
  const employeeTableBody = document.getElementById('employeeTableBody');
  const selectAllEmpCheckbox = document.getElementById('selectAllEmpCheckbox');
  const colCheckboxHeader = document.getElementById('colCheckboxHeader');
  const emptyTableNotice = document.getElementById('emptyTableNotice');

  // Modals
  const addEmployeeModal = document.getElementById('addEmployeeModal');
  const editEmployeeModal = document.getElementById('editEmployeeModal');
  const userDetailModal = document.getElementById('userDetailModal');
  const confirmModal = document.getElementById('confirmModal');

  // Add Form
  const addEmployeeForm = document.getElementById('addEmployeeForm');
  const addName = document.getElementById('addName');
  const addCode = document.getElementById('addCode');
  const addGender = document.getElementById('addGender');
  const addDob = document.getElementById('addDob');
  const addEmail = document.getElementById('addEmail');
  const addUsername = document.getElementById('addUsername');
  const addPassword = document.getElementById('addPassword');

  // Edit Form
  const editEmployeeForm = document.getElementById('editEmployeeForm');
  const editUserId = document.getElementById('editUserId');
  const editName = document.getElementById('editName');
  const editCode = document.getElementById('editCode');
  const editGender = document.getElementById('editGender');
  const editDob = document.getElementById('editDob');
  const editEmail = document.getElementById('editEmail');
  const editUsername = document.getElementById('editUsername');
  const btnSingleDelete = document.getElementById('btnSingleDelete');

  // User Detail View
  const detailName = document.getElementById('detailName');
  const detailCode = document.getElementById('detailCode');
  const detailGender = document.getElementById('detailGender');
  const detailDob = document.getElementById('detailDob');
  const detailEmail = document.getElementById('detailEmail');
  const detailUsername = document.getElementById('detailUsername');
  const detailPassword = document.getElementById('detailPassword');
  const detailFaceStatus = document.getElementById('detailFaceStatus');
  const detailAvatarContainer = document.getElementById('detailAvatarContainer');
  const togglePasswordBtn = document.getElementById('togglePasswordBtn');
  const btnJumpToCalendar = document.getElementById('btnJumpToCalendar');
  const btnRegisterFace = document.getElementById('btnRegisterFace');
  const btnDeleteFace = document.getElementById('btnDeleteFace');
  const faceUploadInput = document.getElementById('faceUploadInput');

  // Confirm Modal
  const confirmMessage = document.getElementById('confirmMessage');
  const btnConfirmAction = document.getElementById('btnConfirmAction');

  let activeDetailUser = null;

  // Unified State Setter for Selected User
  function setSelectedUser(newUser) {
    selectedUser = newUser;

    if (newUser) {
      userSearchInput.value = newUser.name;
      clearSearchBtn.classList.remove('hidden');
      
      selectedName.textContent = newUser.name;
      selectedCode.innerHTML = `<i class="fa-solid fa-id-card"></i> ${newUser.employeeCode || 'Chưa cấp mã'}`;
      selectedGender.innerHTML = `<i class="fa-solid fa-venus-mars"></i> ${newUser.gender || 'Chưa nhập'}`;
      selectedDob.innerHTML = `<i class="fa-solid fa-cake-candles"></i> ${newUser.dob ? formatDateDisplay(newUser.dob) : 'Chưa nhập'}`;
      
      selectedUserStrip.classList.remove('hidden');
    } else {
      userSearchInput.value = '';
      clearSearchBtn.classList.add('hidden');
      selectedUserStrip.classList.add('hidden');
    }

    hideSuggestions();
    loadCheckInHistory();
  }

  // ==========================================
  // 3. SPA TAB SWITCHER LOGIC
  // ==========================================
  function switchTab(tabName) {
    if (tabName === 'calendar') {
      tabBtnCalendar.classList.add('active');
      tabBtnEmployees.classList.remove('active');
      calendarTab.classList.remove('hidden');
      employeesTab.classList.add('hidden');
      if (calendar) {
        setTimeout(() => calendar.updateSize(), 100);
      }
    } else if (tabName === 'employees') {
      tabBtnEmployees.classList.add('active');
      tabBtnCalendar.classList.remove('active');
      employeesTab.classList.remove('hidden');
      calendarTab.classList.add('hidden');
      renderEmployeeTable();
    }
  }

  tabBtnCalendar.addEventListener('click', () => switchTab('calendar'));
  tabBtnEmployees.addEventListener('click', () => switchTab('employees'));

  // ==========================================
  // 4. GRAPHQL HELPER FUNCTION
  // ==========================================
  async function queryGraphQL(query, variables = {}, signal = null) {
    try {
      const response = await fetch('/graphql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, variables }),
        signal: signal
      });

      if (!response.ok) {
        throw new Error(`HTTP Error: ${response.status}`);
      }

      const result = await response.json();
      if (result.errors && result.errors.length > 0) {
        console.warn('GraphQL Query Warnings/Errors:', result.errors);
      }
      return result.data;
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('Previous GraphQL Request Aborted cleanly.');
        return null;
      }
      console.error('GraphQL Fetch Error:', err);
      throw err;
    }
  }

  // ==========================================
  // 5. CALENDAR VIEW LOGIC
  // ==========================================
  const calendarEl = document.getElementById('calendar');
  calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: 'dayGridMonth',
    locale: 'vi',
    eventDisplay: 'block',
    dayMaxEvents: 3,
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'dayGridMonth'
    },
    buttonText: { today: 'Hôm nay', month: 'Tháng' },
    datesSet: function(info) {
      loadCheckInHistory(info.start, info.end);
    },
    dayCellDidMount: function(arg) {
      const dateStr = formatDateToYYYYMMDD(arg.date);
      if (checkedInDates.has(dateStr)) {
        arg.el.classList.add('fc-day-checked-in');
      }
    }
  });
  calendar.render();

  async function loadCheckInHistory(startObj = null, endObj = null) {
    if (!selectedUser) {
      checkedInDates.clear();
      if (calendar) {
        calendar.removeAllEvents();
      }
      document.querySelectorAll('.fc-daygrid-day').forEach(el => {
        el.classList.remove('fc-day-checked-in');
      });
      return;
    }

    let startDateStr, endDateStr;
    if (startObj && endObj) {
      startDateStr = formatDateToYYYYMMDD(startObj);
      endDateStr = formatDateToYYYYMMDD(endObj);
    } else if (calendar) {
      const view = calendar.getView();
      startDateStr = formatDateToYYYYMMDD(view.activeStart);
      endDateStr = formatDateToYYYYMMDD(view.activeEnd);
    } else {
      return;
    }

    if (calendarFetchController) {
      calendarFetchController.abort();
    }
    calendarFetchController = new AbortController();

    const historyQuery = `
      query GetAttendanceHistory($targetUserId: String, $startDate: Date, $endDate: Date) {
        allCheckInHistory(targetUserId: $targetUserId, startDate: $startDate, endDate: $endDate) {
          id
          checkInAt
          checkInDate
          user { id name employeeCode }
        }
      }
    `;

    const data = await queryGraphQL(historyQuery, {
      startDate: startDateStr,
      endDate: endDateStr,
      targetUserId: selectedUser.id
    }, calendarFetchController.signal);

    if (!data || !data.allCheckInHistory) return;

    checkedInDates.clear();
    if (calendar) {
      calendar.removeAllEvents();
    }

    data.allCheckInHistory.forEach(log => {
      const dateStr = log.checkInDate;
      const timeStr = formatIsoTime(log.checkInAt);
      checkedInDates.add(dateStr);

      if (calendar) {
        calendar.addEvent({
          id: log.id,
          title: `✔ Check-in: ${timeStr}`,
          start: dateStr,
          allDay: true,
          backgroundColor: '#10b981',
          borderColor: '#059669',
          textColor: '#ffffff'
        });
      }
    });

    document.querySelectorAll('.fc-daygrid-day').forEach(el => {
      const d = el.getAttribute('data-date');
      if (d && checkedInDates.has(d)) {
        el.classList.add('fc-day-checked-in');
      } else {
        el.classList.remove('fc-day-checked-in');
      }
    });
  }

  // Calendar AutoComplete Search
  let searchTimeout = null;
  userSearchInput.addEventListener('input', (e) => {
    const keyword = e.target.value.trim();
    if (keyword.length > 0) {
      clearSearchBtn.classList.remove('hidden');
    } else {
      clearSearchBtn.classList.add('hidden');
      setSelectedUser(null);
      return;
    }

    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => executeUserSearch(keyword), 200);
  });

  userSearchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (lastSearchResults.length > 0) {
        setSelectedUser(lastSearchResults[0]);
      }
    }
  });

  clearSearchBtn.addEventListener('click', () => setSelectedUser(null));

  async function executeUserSearch(keyword) {
    if (searchAbortController) searchAbortController.abort();
    searchAbortController = new AbortController();

    const searchQuery = `
      query SearchUsers($keyword: String!) {
        searchUsers(keyword: $keyword) {
          id name username email employeeCode gender dob
        }
      }
    `;

    const data = await queryGraphQL(searchQuery, { keyword }, searchAbortController.signal);
    if (!data || !data.searchUsers) return;

    lastSearchResults = data.searchUsers;
    renderSuggestions(data.searchUsers);
  }

  function renderSuggestions(users) {
    searchSuggestions.innerHTML = '';
    if (users.length === 0) {
      searchSuggestions.innerHTML = '<div class="suggestion-item"><span class="suggestion-name" style="color:#94a3b8;">Không tìm thấy nhân viên phù hợp</span></div>';
      searchSuggestions.classList.remove('hidden');
      return;
    }

    users.forEach(u => {
      const item = document.createElement('div');
      item.className = 'suggestion-item';
      const codeTag = u.employeeCode ? `<span class="pill-code">${u.employeeCode}</span>` : '<span class="pill-code">NV-NA</span>';
      
      item.innerHTML = `
        <div class="suggestion-left">
          <span class="suggestion-name">${u.name}</span>
          <div class="suggestion-meta">
            <span>${u.gender || 'Chưa rõ'}</span> | <span>${u.dob ? formatDateDisplay(u.dob) : 'Chưa nhập'}</span>
          </div>
        </div>
        <div>${codeTag}</div>
      `;

      item.addEventListener('click', () => setSelectedUser(u));
      searchSuggestions.appendChild(item);
    });

    searchSuggestions.classList.remove('hidden');
  }

  deselectUserBtn.addEventListener('click', () => setSelectedUser(null));
  function hideSuggestions() { searchSuggestions.classList.add('hidden'); }
  document.addEventListener('click', (e) => {
    if (!userSearchInput.contains(e.target) && !searchSuggestions.contains(e.target)) hideSuggestions();
  });

  jumpDatePicker.addEventListener('change', (e) => {
    if (e.target.value) calendar.gotoDate(e.target.value);
  });

  // ==========================================
  // 6. TAB 2: EMPLOYEE MANAGEMENT LOGIC (GRAPHQL BACKEND INTEGRATION)
  // ==========================================

  // Sortable Columns Listener
  document.querySelectorAll('th.sortable').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.getAttribute('data-col');
      if (sortColumn === col) {
        sortOrder = sortOrder === 'ASC' ? 'DESC' : 'ASC';
      } else {
        sortColumn = col;
        sortOrder = 'ASC';
      }
      updateSortHeaderIcons();
      renderEmployeeTable();
    });
  });

  function updateSortHeaderIcons() {
    document.querySelectorAll('th.sortable').forEach(th => {
      const col = th.getAttribute('data-col');
      const iconSpan = th.querySelector('.sort-icon');
      if (col === sortColumn) {
        iconSpan.textContent = sortOrder === 'ASC' ? '▲' : '▼';
      } else {
        iconSpan.textContent = '';
      }
    });
  }

  // Filter Mode Switching
  empDateFilterMode.addEventListener('change', (e) => {
    const mode = e.target.value;
    if (mode === 'exact') {
      empExactDatePicker.classList.remove('hidden');
      empStartDatePicker.classList.add('hidden');
      empEndDatePicker.classList.add('hidden');
      rangeSeparator.classList.add('hidden');
    } else {
      empExactDatePicker.classList.add('hidden');
      empStartDatePicker.classList.remove('hidden');
      empEndDatePicker.classList.remove('hidden');
      rangeSeparator.classList.remove('hidden');
    }
    renderEmployeeTable();
  });

  empSearchInput.addEventListener('input', () => renderEmployeeTable());
  empExactDatePicker.addEventListener('change', () => renderEmployeeTable());
  empStartDatePicker.addEventListener('change', () => renderEmployeeTable());
  empEndDatePicker.addEventListener('change', () => renderEmployeeTable());

  btnClearEmpFilters.addEventListener('click', () => {
    empSearchInput.value = '';
    empDateFilterMode.value = 'exact';
    empExactDatePicker.value = '';
    empStartDatePicker.value = '';
    empEndDatePicker.value = '';
    empExactDatePicker.classList.remove('hidden');
    empStartDatePicker.classList.add('hidden');
    empEndDatePicker.classList.add('hidden');
    rangeSeparator.classList.add('hidden');
    renderEmployeeTable();
  });

  // Render Employee Table Grid via GraphQL Paginated Query
  async function renderEmployeeTable() {
    if (empTableFetchController) empTableFetchController.abort();
    empTableFetchController = new AbortController();

    const keyword = empSearchInput.value.trim();
    const filterMode = empDateFilterMode.value;

    let dateFilter = null;
    let startDate = null;
    let endDate = null;

    if (filterMode === 'exact' && empExactDatePicker.value) {
      dateFilter = empExactDatePicker.value;
    } else if (filterMode === 'range') {
      if (empStartDatePicker.value) startDate = empStartDatePicker.value;
      if (empEndDatePicker.value) endDate = empEndDatePicker.value;
    }

    const paginatedQuery = `
      query GetPaginatedEmployees(
        $keyword: String,
        $dateFilter: Date,
        $startDate: Date,
        $endDate: Date,
        $sortBy: String,
        $sortOrder: String
      ) {
        paginatedUsers(
          keyword: $keyword,
          dateFilter: $dateFilter,
          startDate: $startDate,
          endDate: $endDate,
          sortBy: $sortBy,
          sortOrder: $sortOrder,
          page: 1,
          pageSize: 100
        ) {
          totalCount
          items {
            id
            name
            username
            email
            employeeCode
            gender
            dob
            password
            hasRegisteredFace
            faceId
            isActive
            isAdmin
            createdAt
          }
        }
      }
    `;

    const variables = {
      keyword: keyword || null,
      dateFilter: dateFilter,
      startDate: startDate,
      endDate: endDate,
      sortBy: sortColumn,
      sortOrder: sortOrder
    };

    const data = await queryGraphQL(paginatedQuery, variables, empTableFetchController.signal);
    if (!data || !data.paginatedUsers) return;

    currentEmployeesList = data.paginatedUsers.items;

    // Render Tbody Rows
    employeeTableBody.innerHTML = '';
    if (currentEmployeesList.length === 0) {
      emptyTableNotice.classList.remove('hidden');
    } else {
      emptyTableNotice.classList.add('hidden');
    }

    currentEmployeesList.forEach(emp => {
      // Add to FIFO cache
      employeeCache.set(emp.id, emp);

      const tr = document.createElement('tr');
      if (bulkSelectedIds.has(emp.id)) {
        tr.classList.add('row-selected');
      }

      const checkboxTd = isBulkDeleteMode 
        ? `<td class="col-checkbox" onclick="event.stopPropagation()">
            <input type="checkbox" class="emp-row-checkbox" data-id="${emp.id}" ${bulkSelectedIds.has(emp.id) ? 'checked' : ''} />
           </td>`
        : `<td class="col-checkbox hidden"></td>`;

      tr.innerHTML = `
        ${checkboxTd}
        <td><span class="pill-code">${emp.employeeCode || 'NV-NA'}</span></td>
        <td class="text-bold">${emp.name}</td>
        <td>${emp.gender || 'Chưa nhập'}</td>
        <td>${emp.dob ? formatDateDisplay(emp.dob) : 'Chưa nhập'}</td>
        <td>${emp.createdAt ? formatDateDisplay(emp.createdAt.split('T')[0]) : 'Chưa nhập'}</td>
        <td><span style="color: var(--accent-cyan);">${emp.username || emp.employeeCode}</span></td>
      `;

      tr.addEventListener('click', () => {
        if (isBulkDeleteMode) {
          toggleSelectUser(emp.id);
        } else {
          openUserDetailModal(emp);
        }
      });

      employeeTableBody.appendChild(tr);
    });

    document.querySelectorAll('.emp-row-checkbox').forEach(cb => {
      cb.addEventListener('change', (e) => {
        const id = e.target.getAttribute('data-id');
        toggleSelectUser(id, e.target.checked);
      });
    });
  }

  function toggleSelectUser(id, forceValue = null) {
    if (forceValue !== null) {
      if (forceValue) bulkSelectedIds.add(id);
      else bulkSelectedIds.delete(id);
    } else {
      if (bulkSelectedIds.has(id)) bulkSelectedIds.delete(id);
      else bulkSelectedIds.add(id);
    }
    bulkSelectCount.textContent = bulkSelectedIds.size;
    renderEmployeeTable();
  }

  selectAllEmpCheckbox.addEventListener('change', (e) => {
    if (e.target.checked) {
      currentEmployeesList.forEach(u => bulkSelectedIds.add(u.id));
    } else {
      bulkSelectedIds.clear();
    }
    bulkSelectCount.textContent = bulkSelectedIds.size;
    renderEmployeeTable();
  });

  // Bulk Delete Mode Toggle
  btnBulkDeleteMode.addEventListener('click', () => {
    isBulkDeleteMode = true;
    bulkSelectedIds.clear();
    bulkSelectCount.textContent = '0';
    standardActionBar.classList.add('hidden');
    bulkActionBar.classList.remove('hidden');
    colCheckboxHeader.classList.remove('hidden');
    renderEmployeeTable();
  });

  btnCancelBulk.addEventListener('click', () => {
    isBulkDeleteMode = false;
    bulkSelectedIds.clear();
    standardActionBar.classList.remove('hidden');
    bulkActionBar.classList.add('hidden');
    colCheckboxHeader.classList.add('hidden');
    renderEmployeeTable();
  });

  btnConfirmBulkDelete.addEventListener('click', () => {
    if (bulkSelectedIds.size === 0) {
      alert('Vui lòng chọn ít nhất 1 nhân viên để xóa!');
      return;
    }

    openConfirmModal(
      `Bạn có chắc chắn muốn xóa hàng loạt <b>${bulkSelectedIds.size}</b> nhân viên đã chọn không?`,
      async () => {
        const bulkMutation = `
          mutation BulkDelete($ids: [String!]!) {
            bulkDeleteUsers(ids: $ids)
          }
        `;
        const idsArray = Array.from(bulkSelectedIds);
        await queryGraphQL(bulkMutation, { ids: idsArray });
        btnCancelBulk.click(); // Exit bulk mode & re-render
      }
    );
  });

  // ==========================================
  // 7. MODALS & GRAPHQL MUTATIONS INTEGRATION
  // ==========================================
  function openModal(modalEl) { modalEl.classList.remove('hidden'); }
  function closeModal(modalEl) { modalEl.classList.add('hidden'); }

  document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', () => {
      const modalId = btn.getAttribute('data-close');
      closeModal(document.getElementById(modalId));
    });
  });

  // Modal 1: Add Employee via GraphQL Mutation
  btnAddEmployee.addEventListener('click', () => {
    addEmployeeForm.reset();
    openModal(addEmployeeModal);
  });

  addEmployeeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const nameVal = addName.value.trim();
    if (!nameVal) return;

    const createMutation = `
      mutation CreateEmp($input: UserCreateInput!) {
        createUser(input: $input) {
          id name employeeCode username password gender dob email
        }
      }
    `;

    const input = {
      name: nameVal,
      employeeCode: addCode.value.trim() || null,
      username: addUsername.value.trim() || null,
      password: addPassword.value.trim() || null,
      gender: addGender.value || null,
      dob: addDob.value || null,
      email: addEmail.value.trim() || null
    };

    const data = await queryGraphQL(createMutation, { input });
    if (data && data.createUser) {
      closeModal(addEmployeeModal);
      renderEmployeeTable();
    }
  });

  // Modal 2: Edit Employee via GraphQL Mutation
  btnEditEmployee.addEventListener('click', () => {
    if (currentEmployeesList.length === 0) return;
    openEditEmployeeModal(currentEmployeesList[0]);
  });

  function openEditEmployeeModal(emp) {
    editUserId.value = emp.id;
    editName.value = emp.name;
    editCode.value = emp.employeeCode || '';
    editGender.value = emp.gender || 'Nam';
    editDob.value = emp.dob || '';
    editEmail.value = emp.email || '';
    editUsername.value = emp.username || '';
    openModal(editEmployeeModal);
  }

  editEmployeeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = editUserId.value;

    const updateMutation = `
      mutation UpdateEmp($id: String!, $input: UserUpdateInput!) {
        updateUser(id: $id, input: $input) {
          id name employeeCode username gender dob email
        }
      }
    `;

    const input = {
      name: editName.value.trim() || null,
      employeeCode: editCode.value.trim() || null,
      username: editUsername.value.trim() || null,
      gender: editGender.value || null,
      dob: editDob.value || null,
      email: editEmail.value.trim() || null
    };

    const data = await queryGraphQL(updateMutation, { id, input });
    if (data && data.updateUser) {
      closeModal(editEmployeeModal);
      renderEmployeeTable();
    }
  });

  btnSingleDelete.addEventListener('click', () => {
    const id = editUserId.value;
    const emp = currentEmployeesList.find(u => u.id === id);
    if (!emp) return;

    openConfirmModal(
      `Bạn có chắc chắn muốn xóa nhân viên <b>${emp.name}</b> (${emp.employeeCode}) không?`,
      async () => {
        const deleteMutation = `
          mutation DeleteEmp($id: String!) {
            deleteUser(id: $id)
          }
        `;
        await queryGraphQL(deleteMutation, { id });
        closeModal(editEmployeeModal);
        renderEmployeeTable();
      }
    );
  });

  // Modal 3: User Detail Modal (With Password & History Jump Button)
  function openUserDetailModal(emp) {
    activeDetailUser = emp;
    detailName.textContent = emp.name;
    detailCode.textContent = emp.employeeCode || 'Chưa cấp mã';
    detailGender.textContent = emp.gender || 'Chưa nhập';
    detailDob.textContent = emp.dob ? formatDateDisplay(emp.dob) : 'Chưa nhập';
    detailEmail.textContent = emp.email || 'Chưa nhập';
    detailUsername.textContent = emp.username || emp.employeeCode;
    detailPassword.value = emp.password || 'pwd_123456';
    detailPassword.type = 'password';

    if (emp.hasRegisteredFace) {
      detailFaceStatus.innerHTML = '<span class="face-badge-registered"><i class="fa-solid fa-face-smile"></i> 🟢 Đã đăng ký (FAISS 128D Vector)</span>';
      if (btnDeleteFace) btnDeleteFace.classList.remove('hidden');
      if (detailAvatarContainer) {
        detailAvatarContainer.innerHTML = `<img src="/api/admin/face/cropped-image/${emp.id}?t=${Date.now()}" alt="${emp.name}" onerror="this.outerHTML='<i class=\\'fa-solid fa-user\\'></i>'" />`;
      }
    } else {
      detailFaceStatus.innerHTML = '<span class="face-badge-unregistered"><i class="fa-solid fa-face-frown"></i> 🔴 Chưa đăng ký khuôn mặt</span>';
      if (btnDeleteFace) btnDeleteFace.classList.add('hidden');
      if (detailAvatarContainer) {
        detailAvatarContainer.innerHTML = '<i class="fa-solid fa-user"></i>';
      }
    }

    openModal(userDetailModal);
  }

  togglePasswordBtn.addEventListener('click', () => {
    if (detailPassword.type === 'password') {
      detailPassword.type = 'text';
      togglePasswordBtn.innerHTML = '<i class="fa-solid fa-eye-slash"></i>';
    } else {
      detailPassword.type = 'password';
      togglePasswordBtn.innerHTML = '<i class="fa-solid fa-eye"></i>';
    }
  });

  btnJumpToCalendar.addEventListener('click', () => {
    if (!activeDetailUser) return;
    closeModal(userDetailModal);
    switchTab('calendar');
    setSelectedUser(activeDetailUser);
  });

  // Admin Register Face Action
  if (btnRegisterFace && faceUploadInput) {
    btnRegisterFace.addEventListener('click', () => {
      faceUploadInput.click();
    });

    faceUploadInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file || !activeDetailUser) return;

      const formData = new FormData();
      formData.append('user_id', activeDetailUser.id);
      formData.append('file', file);

      btnRegisterFace.disabled = true;
      btnRegisterFace.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang đăng ký...';

      try {
        const response = await fetch('/api/admin/face/register', {
          method: 'POST',
          body: formData
        });

        const resData = await response.json();
        if (response.ok) {
          alert(`Đăng ký khuôn mặt thành công cho nhân viên: ${resData.name}!`);
          activeDetailUser.hasRegisteredFace = true;
          detailFaceStatus.innerHTML = '<span class="face-badge-registered"><i class="fa-solid fa-face-smile"></i> 🟢 Đã đăng ký (FAISS 128D Vector)</span>';
          renderEmployeeTable();
        } else {
          const errorMsg = resData.error_message || resData.detail || 'Không thể xử lý tệp ảnh';
          alert(`Lỗi đăng ký khuôn mặt: ${errorMsg}`);
        }
      } catch (err) {
        console.error('Register Face Error:', err);
        alert('Đã xảy ra lỗi hệ thống khi gửi ảnh đăng ký khuôn mặt.');
      } finally {
        btnRegisterFace.disabled = false;
        btnRegisterFace.innerHTML = '<i class="fa-solid fa-camera"></i> 📸 Đăng ký Khuôn mặt';
        faceUploadInput.value = '';
      }
    });
  }

  // Admin Delete Face Action
  if (btnDeleteFace) {
    btnDeleteFace.addEventListener('click', () => {
      if (!activeDetailUser) return;

      openConfirmModal(
        `Bạn có chắc chắn muốn xóa khuôn mặt đã đăng ký của nhân viên <b>${activeDetailUser.name}</b> (${activeDetailUser.employeeCode}) không?`,
        async () => {
          try {
            const response = await fetch(`/api/admin/face/${activeDetailUser.id}`, {
              method: 'DELETE'
            });

            const resData = await response.json();
            if (response.ok) {
              alert(`Xóa khuôn mặt thành công cho nhân viên: ${activeDetailUser.name}!`);
              activeDetailUser.hasRegisteredFace = false;
              detailFaceStatus.innerHTML = '<span class="face-badge-unregistered"><i class="fa-solid fa-face-frown"></i> 🔴 Chưa đăng ký khuôn mặt</span>';
              btnDeleteFace.classList.add('hidden');
              if (detailAvatarContainer) {
                detailAvatarContainer.innerHTML = '<i class="fa-solid fa-user"></i>';
              }
              renderEmployeeTable();
            } else {
              const errorMsg = resData.error_message || resData.detail || 'Không thể thực hiện';
              alert(`Lỗi xóa khuôn mặt: ${errorMsg}`);
            }
          } catch (err) {
            console.error('Delete Face Error:', err);
            alert('Đã xảy ra lỗi hệ thống khi xóa khuôn mặt.');
          }
        }
      );
    });
  }

  // Modal 4: Confirm Action Modal
  function openConfirmModal(message, actionFn) {
    confirmMessage.innerHTML = message;
    pendingDeleteAction = actionFn;
    openModal(confirmModal);
  }

  btnConfirmAction.addEventListener('click', async () => {
    if (pendingDeleteAction) {
      await pendingDeleteAction();
      pendingDeleteAction = null;
    }
    closeModal(confirmModal);
  });

  // ==========================================
  // 12. FACE RECOGNITION SEARCH LOGIC
  // ==========================================
  const faceSearchModal = document.getElementById('faceSearchModal');
  const btnOpenFaceSearch = document.getElementById('btnOpenFaceSearch');
  const faceSearchFileInput = document.getElementById('faceSearchFileInput');
  const btnSelectFaceSearchPhoto = document.getElementById('btnSelectFaceSearchPhoto');
  const cropperContainer = document.getElementById('cropperContainer');
  const cropperCanvas = document.getElementById('cropperCanvas');
  const cropDimensionsText = document.getElementById('cropDimensionsText');
  const cropperWarningNotice = document.getElementById('cropperWarningNotice');
  const btnExecuteFaceSearch = document.getElementById('btnExecuteFaceSearch');

  let originalImage = null;
  let scaleFactor = 1.0;
  
  // Crop box: aspect ratio 4:6 (w:h = 1:1.5)
  let cropBox = { x: 50, y: 50, w: 100, h: 150 };
  let isDragging = false;
  let isResizing = false;
  let dragStart = { x: 0, y: 0 };
  const handleSize = 15; // Resize handle bottom-right corner

  if (btnOpenFaceSearch) {
    btnOpenFaceSearch.addEventListener('click', () => {
      // Reset state
      originalImage = null;
      cropperContainer.classList.add('hidden');
      btnExecuteFaceSearch.classList.add('hidden');
      btnExecuteFaceSearch.disabled = true;
      faceSearchFileInput.value = '';
      openModal(faceSearchModal);
    });
  }

  if (btnSelectFaceSearchPhoto) {
    btnSelectFaceSearchPhoto.addEventListener('click', () => {
      faceSearchFileInput.click();
    });
  }

  if (faceSearchFileInput) {
    faceSearchFileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        originalImage = new Image();
        originalImage.onload = () => {
          initializeCropper();
        };
        originalImage.src = event.target.result;
      };
      reader.readAsDataURL(file);
    });
  }

  function initializeCropper() {
    cropperContainer.classList.remove('hidden');
    btnExecuteFaceSearch.classList.remove('hidden');

    const maxW = 500;
    const maxH = 380;
    let canvasW = originalImage.naturalWidth;
    let canvasH = originalImage.naturalHeight;

    // Scale to fit max boundaries
    if (canvasW > maxW) {
      canvasH = (maxW / canvasW) * canvasH;
      canvasW = maxW;
    }
    if (canvasH > maxH) {
      canvasW = (maxH / canvasH) * canvasW;
      canvasH = maxH;
    }

    cropperCanvas.width = canvasW;
    cropperCanvas.height = canvasH;
    scaleFactor = canvasW / originalImage.naturalWidth;

    // Default crop box: centered, width = 30% of canvas, aspect ratio 4:6
    const boxW = Math.max(80, Math.min(canvasW * 0.4, 200));
    const boxH = boxW * 1.5;
    cropBox = {
      x: (canvasW - boxW) / 2,
      y: (canvasH - boxH) / 2,
      w: boxW,
      h: boxH
    };

    drawCropper();
    updateCropMetrics();
  }

  function drawCropper() {
    const ctx = cropperCanvas.getContext('2d');
    if (!ctx || !originalImage) return;

    // 1. Draw original image
    ctx.drawImage(originalImage, 0, 0, cropperCanvas.width, cropperCanvas.height);

    // 2. Draw semi-transparent dark overlay outside crop box
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    
    // Top
    ctx.fillRect(0, 0, cropperCanvas.width, cropBox.y);
    // Bottom
    ctx.fillRect(0, cropBox.y + cropBox.h, cropperCanvas.width, cropperCanvas.height - (cropBox.y + cropBox.h));
    // Left
    ctx.fillRect(0, cropBox.y, cropBox.x, cropBox.h);
    // Right
    ctx.fillRect(cropBox.x + cropBox.w, cropBox.y, cropperCanvas.width - (cropBox.x + cropBox.w), cropBox.h);

    // 3. Draw crop box border
    ctx.strokeStyle = 'var(--accent-cyan)';
    ctx.lineWidth = 2;
    ctx.strokeRect(cropBox.x, cropBox.y, cropBox.w, cropBox.h);

    // 4. Draw resize handle (bottom-right corner)
    ctx.fillStyle = 'var(--accent-cyan)';
    ctx.beginPath();
    ctx.arc(cropBox.x + cropBox.w, cropBox.y + cropBox.h, 6, 0, 2 * Math.PI);
    ctx.fill();
    
    // Draw outer guide circle for resize handle
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(cropBox.x + cropBox.w, cropBox.y + cropBox.h, 10, 0, 2 * Math.PI);
    ctx.stroke();
  }

  function updateCropMetrics() {
    const origW = Math.round(cropBox.w / scaleFactor);
    const origH = Math.round(cropBox.h / scaleFactor);

    cropDimensionsText.textContent = `${origW} x ${origH}`;

    // Refuse if cropped area size is too small on original image (< 80px)
    if (origW < 80 || origH < 80) {
      cropperWarningNotice.classList.remove('hidden');
      btnExecuteFaceSearch.disabled = true;
    } else {
      cropperWarningNotice.classList.add('hidden');
      btnExecuteFaceSearch.disabled = false;
    }
  }

  // Interactive mouse/touch events on canvas
  function getMousePos(e) {
    const rect = cropperCanvas.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return {
      x: clientX - rect.left,
      y: clientY - rect.top
    };
  }

  function handleStart(e) {
    if (!originalImage) return;
    const pos = getMousePos(e);

    // Check if clicking resize handle (bottom-right corner)
    const handleX = cropBox.x + cropBox.w;
    const handleY = cropBox.y + cropBox.h;
    const dist = Math.hypot(pos.x - handleX, pos.y - handleY);

    if (dist <= handleSize) {
      isResizing = true;
      e.preventDefault();
    } else if (
      pos.x >= cropBox.x &&
      pos.x <= cropBox.x + cropBox.w &&
      pos.y >= cropBox.y &&
      pos.y <= cropBox.y + cropBox.h
    ) {
      isDragging = true;
      dragStart = {
        x: pos.x - cropBox.x,
        y: pos.y - cropBox.y
      };
      e.preventDefault();
    }
  }

  function handleMove(e) {
    if (!originalImage || (!isDragging && !isResizing)) return;
    const pos = getMousePos(e);

    if (isDragging) {
      cropBox.x = pos.x - dragStart.x;
      cropBox.y = pos.y - dragStart.y;

      // Bound clamping
      cropBox.x = Math.max(0, Math.min(cropBox.x, cropperCanvas.width - cropBox.w));
      cropBox.y = Math.max(0, Math.min(cropBox.y, cropperCanvas.height - cropBox.h));
    }

    if (isResizing) {
      let newW = pos.x - cropBox.x;
      // Maintain 4:6 aspect ratio (h = w * 1.5)
      let newH = newW * 1.5;

      // Keep minimum size
      if (newW < 30) {
        newW = 30;
        newH = 45;
      }

      // Bound clamping
      if (cropBox.x + newW > cropperCanvas.width) {
        newW = cropperCanvas.width - cropBox.x;
        newH = newW * 1.5;
      }
      if (cropBox.y + newH > cropperCanvas.height) {
        newH = cropperCanvas.height - cropBox.y;
        newW = newH / 1.5;
      }

      cropBox.w = newW;
      cropBox.h = newH;
    }

    drawCropper();
    updateCropMetrics();
    e.preventDefault();
  }

  function handleEnd() {
    isDragging = false;
    isResizing = false;
  }

  if (cropperCanvas) {
    cropperCanvas.addEventListener('mousedown', handleStart);
    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleEnd);

    // Mobile touch events
    cropperCanvas.addEventListener('touchstart', handleStart, { passive: false });
    window.addEventListener('touchmove', handleMove, { passive: false });
    window.addEventListener('touchend', handleEnd);
  }

  // Execute Face Search (Recognize API call)
  if (btnExecuteFaceSearch) {
    btnExecuteFaceSearch.addEventListener('click', () => {
      if (!originalImage) return;

      const origX = cropBox.x / scaleFactor;
      const origY = cropBox.y / scaleFactor;
      const origW = cropBox.w / scaleFactor;
      const origH = cropBox.h / scaleFactor;

      // Final check for safety
      if (origW < 80 || origH < 80) {
        alert('Vùng cắt quá nhỏ (yêu cầu tối thiểu 80x80px). Không thể gửi đi.');
        return;
      }

      // Create cropped Canvas
      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = origW;
      tempCanvas.height = origH;
      const tempCtx = tempCanvas.getContext('2d');
      
      if (!tempCtx) {
        alert('Lỗi tạo Canvas ảo để cắt ảnh.');
        return;
      }

      tempCtx.drawImage(
        originalImage,
        origX, origY, origW, origH, // Source
        0, 0, origW, origH          // Target
      );

      btnExecuteFaceSearch.disabled = true;
      btnExecuteFaceSearch.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tìm kiếm...';

      tempCanvas.toBlob(async (blob) => {
        if (!blob) {
          alert('Lỗi chuyển đổi ảnh cắt sang tệp nhị phân.');
          btnExecuteFaceSearch.disabled = false;
          btnExecuteFaceSearch.innerHTML = '<i class="fa-solid fa-bolt"></i> Bắt đầu nhận diện';
          return;
        }

        const formData = new FormData();
        formData.append('file', blob, 'face_crop.jpg');

        try {
          const response = await fetch('/api/admin/face/recognize', {
            method: 'POST',
            body: formData
          });

          const resData = await response.json();
          if (response.ok) {
            if (resData.match && resData.user_id) {
              alert(`Nhận diện thành công! Nhân viên: ${resData.name} (${resData.employee_code || 'Không có mã'})`);
              closeModal(faceSearchModal);
              
              // Find employee in local list and open detail modal
              const localEmp = currentEmployeesList.find(u => u.id === resData.user_id);
              if (localEmp) {
                openUserDetailModal(localEmp);
              } else {
                // If not found in current page, query details from GraphQL
                const detailsQuery = `
                  query GetUser($id: String!) {
                    user(id: $id) {
                      id name employeeCode username gender dob email password hasRegisteredFace
                    }
                  }
                `;
                const qData = await queryGraphQL(detailsQuery, { id: resData.user_id });
                if (qData && qData.user) {
                  openUserDetailModal(qData.user);
                } else {
                  alert('Không thể tải hồ sơ chi tiết của nhân viên vừa nhận diện.');
                }
              }
            } else {
              alert(resData.message || 'Không tìm thấy khuôn mặt trùng khớp trong cơ sở dữ liệu.');
            }
          } else {
            alert(`Lỗi nhận diện: ${resData.detail || resData.error_message || 'Ảnh không hợp lệ.'}`);
          }
        } catch (err) {
          console.error('Face Search Error:', err);
          alert('Đã xảy ra lỗi hệ thống khi kết nối tới máy chủ nhận diện.');
        } finally {
          btnExecuteFaceSearch.disabled = false;
          btnExecuteFaceSearch.innerHTML = '<i class="fa-solid fa-bolt"></i> Bắt đầu nhận diện';
        }
      }, 'image/jpeg', 0.95);
    });
  }

  // Utility Formatters
  function formatDateToYYYYMMDD(dateObj) {
    const d = new Date(dateObj);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function formatDateDisplay(dateStr) {
    if (!dateStr) return '';
    const cleanStr = String(dateStr).split('T')[0];
    const parts = cleanStr.split('-');
    if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
    return dateStr;
  }

  function formatIsoTime(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const seconds = String(d.getSeconds()).padStart(2, '0');
    return `${hours}:${minutes}:${seconds}`;
  }
});
