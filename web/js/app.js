/* =============================================================================
   app.js — Основная логика SPA-приложения HotelMS
   ============================================================================= */

// ── Утилиты ──────────────────────────────────────────────────────────────────

function toast(msg, type = 'info') {
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    const icon = type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle';
    el.innerHTML = `<i class="fas fa-${icon}"></i> ${msg}`;
    document.getElementById('toasts').appendChild(el);
    setTimeout(() => el.remove(), 4000);
}

function openModal(html) {
    document.getElementById('modalContent').innerHTML = html;
    document.getElementById('modal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('modal').classList.add('hidden');
}

function formatDate(d) {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function formatMoney(n) {
    return Number(n).toLocaleString('ru-RU') + ' \u20BD';
}

const STATUS_LABELS = {
    available: 'Свободен', occupied: 'Занят', maintenance: 'Ремонт',
    pending: 'Ожидание', confirmed: 'Подтверждено', checked_in: 'Заселён',
    checked_out: 'Выселен', cancelled: 'Отменено', completed: 'Завершено'
};

const ROLE_LABELS = { admin: 'Администратор', manager: 'Менеджер', guest: 'Гость' };

const AMENITY_ICONS = {
    wifi: 'fa-wifi', snowflake: 'fa-snowflake', wine: 'fa-wine-glass',
    tv: 'fa-tv', lock: 'fa-lock', wind: 'fa-wind', shirt: 'fa-shirt',
    sun: 'fa-sun', droplets: 'fa-droplet', laptop: 'fa-laptop',
    coffee: 'fa-mug-hot', building: 'fa-building'
};

// ── Навигация ────────────────────────────────────────────────────────────────

function renderNav() {
    const links = document.getElementById('navLinks');
    const userEl = document.getElementById('navUser');

    if (!api.isAuth()) {
        links.innerHTML = '';
        userEl.innerHTML = '';
        return;
    }

    let nav = `
        <a onclick="navigate('rooms')" id="nav-rooms"><i class="fas fa-bed"></i> Номера</a>
        <a onclick="navigate('my-bookings')" id="nav-my-bookings"><i class="fas fa-calendar"></i> Мои бронирования</a>
        <a onclick="navigate('profile')" id="nav-profile"><i class="fas fa-user"></i> Профиль</a>
    `;
    if (api.isStaff()) {
        nav += `<a onclick="navigate('admin')" id="nav-admin"><i class="fas fa-cog"></i> Управление</a>`;
    }
    links.innerHTML = nav;

    userEl.innerHTML = `
        <div class="user-info">
            <div>${api.user.email}</div>
            <span class="user-role">${ROLE_LABELS[api.user.role] || api.user.role}</span>
        </div>
        <button class="btn-logout" onclick="doLogout()"><i class="fas fa-sign-out-alt"></i> Выйти</button>
    `;
}

let currentPage = '';

function navigate(page) {
    currentPage = page;
    document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));
    const active = document.getElementById('nav-' + page);
    if (active) active.classList.add('active');

    const app = document.getElementById('app');
    switch (page) {
        case 'login': renderLogin(app); break;
        case 'register': renderRegister(app); break;
        case 'rooms': renderRooms(app); break;
        case 'my-bookings': renderMyBookings(app); break;
        case 'profile': renderProfile(app); break;
        case 'admin': renderAdmin(app); break;
        default: renderRooms(app);
    }
}

function doLogout() {
    api.logout();
    renderNav();
    navigate('login');
    toast('Вы вышли из системы', 'info');
}

// ── Страница входа ───────────────────────────────────────────────────────────

function renderLogin(app) {
    app.innerHTML = `
    <div class="auth-page">
        <div class="auth-card">
            <div class="auth-icon"><i class="fas fa-hotel"></i></div>
            <h2>Вход в систему</h2>
            <p class="subtitle">Система управления гостиницей HotelMS</p>
            <form id="loginForm">
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" id="loginEmail" placeholder="email@example.com" required>
                </div>
                <div class="form-group">
                    <label>Пароль</label>
                    <input type="password" id="loginPass" placeholder="Введите пароль" required>
                </div>
                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-sign-in-alt"></i> Войти
                </button>
            </form>
            <div class="auth-link">
                Нет аккаунта? <a onclick="navigate('register')">Зарегистрироваться</a>
            </div>
        </div>
    </div>`;

    document.getElementById('loginForm').onsubmit = async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Вход...';
        try {
            const data = await api.login(
                document.getElementById('loginEmail').value,
                document.getElementById('loginPass').value
            );
            api.setAuth(data);
            renderNav();
            navigate('rooms');
            toast('Добро пожаловать!', 'success');
        } catch (err) {
            toast(err.message, 'error');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Войти';
        }
    };
}

// ── Страница регистрации ─────────────────────────────────────────────────────

function renderRegister(app) {
    app.innerHTML = `
    <div class="auth-page">
        <div class="auth-card">
            <div class="auth-icon"><i class="fas fa-user-plus"></i></div>
            <h2>Регистрация</h2>
            <p class="subtitle">Создайте аккаунт для бронирования номеров</p>
            <form id="regForm">
                <div class="form-row">
                    <div class="form-group">
                        <label>Имя</label>
                        <input type="text" id="regFirst" placeholder="Иван" required>
                    </div>
                    <div class="form-group">
                        <label>Фамилия</label>
                        <input type="text" id="regLast" placeholder="Иванов" required>
                    </div>
                </div>
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" id="regEmail" placeholder="email@example.com" required>
                </div>
                <div class="form-group">
                    <label>Телефон</label>
                    <input type="tel" id="regPhone" placeholder="+79001234567">
                </div>
                <div class="form-group">
                    <label>Пароль</label>
                    <input type="password" id="regPass" placeholder="Минимум 6 символов" minlength="6" required>
                </div>
                <div class="form-group">
                    <label>Подтверждение пароля</label>
                    <input type="password" id="regPass2" placeholder="Повторите пароль" required>
                </div>
                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-user-plus"></i> Создать аккаунт
                </button>
            </form>
            <div class="auth-link">
                Уже есть аккаунт? <a onclick="navigate('login')">Войти</a>
            </div>
        </div>
    </div>`;

    document.getElementById('regForm').onsubmit = async (e) => {
        e.preventDefault();
        const pass = document.getElementById('regPass').value;
        if (pass !== document.getElementById('regPass2').value) {
            toast('Пароли не совпадают', 'error');
            return;
        }
        const btn = e.target.querySelector('button');
        btn.disabled = true;
        try {
            const body = {
                email: document.getElementById('regEmail').value,
                password: pass,
                first_name: document.getElementById('regFirst').value,
                last_name: document.getElementById('regLast').value,
            };
            const phone = document.getElementById('regPhone').value;
            if (phone) body.phone = phone;
            const data = await api.register(body);
            api.setAuth(data);
            renderNav();
            navigate('rooms');
            toast('Регистрация успешна!', 'success');
        } catch (err) {
            toast(err.message, 'error');
            btn.disabled = false;
        }
    };
}

// ── Каталог номеров ──────────────────────────────────────────────────────────

let allCategories = [];

async function renderRooms(app) {
    app.innerHTML = `
        <div class="page-header">
            <h1><i class="fas fa-bed"></i> Каталог номеров</h1>
        </div>
        <div class="filters-bar" id="filtersBar">Загрузка фильтров...</div>
        <div class="rooms-grid" id="roomsGrid"><div class="spinner"></div></div>
    `;

    try {
        allCategories = await api.getCategories();
        renderFilters();
        await loadRooms();
    } catch (err) {
        toast(err.message, 'error');
    }
}

function renderFilters() {
    const catOpts = allCategories.map(c => `<option value="${c.id}">${c.name} — ${formatMoney(c.base_price)}</option>`).join('');
    document.getElementById('filtersBar').innerHTML = `
        <select id="filterCat" onchange="loadRooms()">
            <option value="">Все категории</option>
            ${catOpts}
        </select>
        <select id="filterStatus" onchange="loadRooms()">
            <option value="">Любой статус</option>
            <option value="available">Свободен</option>
            <option value="occupied">Занят</option>
            <option value="maintenance">На ремонте</option>
        </select>
        <select id="filterFloor" onchange="loadRooms()">
            <option value="">Любой этаж</option>
            <option value="1">1 этаж</option>
            <option value="2">2 этаж</option>
            <option value="3">3 этаж</option>
            <option value="4">4 этаж</option>
            <option value="5">5 этаж</option>
        </select>
    `;
}

async function loadRooms() {
    const grid = document.getElementById('roomsGrid');
    grid.innerHTML = '<div class="spinner"></div>';
    const params = {};
    const cat = document.getElementById('filterCat')?.value;
    const status = document.getElementById('filterStatus')?.value;
    const floor = document.getElementById('filterFloor')?.value;
    if (cat) params.category_id = cat;
    if (status) params.status = status;
    if (floor) params.floor = floor;

    try {
        const rooms = await api.getRooms(params);
        if (!rooms.length) {
            grid.innerHTML = `<div class="empty-state"><i class="fas fa-search"></i><p>Номера не найдены</p></div>`;
            return;
        }
        grid.innerHTML = rooms.map(r => {
            const cat = allCategories.find(c => c.id === r.category_id) || {};
            const amenities = (r.amenities || []).slice(0, 5).map(a =>
                `<span class="amenity-tag"><i class="fas ${AMENITY_ICONS[a.icon] || 'fa-star'}"></i> ${a.name}</span>`
            ).join('');
            const canBook = r.status === 'available';
            return `
            <div class="room-card">
                <div class="room-card-img" style="background: linear-gradient(135deg, 
                    ${r.floor <= 2 ? '#1565C0, #42A5F5' : r.floor <= 3 ? '#2E7D32, #66BB6A' : r.floor <= 4 ? '#E65100, #FF9800' : '#6A1B9A, #AB47BC'})">
                    <i class="fas fa-bed"></i>
                    <span class="room-status status-${r.status}">${STATUS_LABELS[r.status]}</span>
                </div>
                <div class="room-card-body">
                    <h3>Номер ${r.room_number}</h3>
                    <div class="room-cat">${cat.name || ''} &bull; ${r.floor} этаж &bull; до ${cat.capacity || '?'} гостей</div>
                    <div class="room-desc">${r.description || ''}</div>
                    <div class="room-amenities">${amenities}</div>
                    <div class="room-meta">
                        <div class="room-price">${formatMoney(cat.base_price || 0)} <span>/ ночь</span></div>
                        ${canBook ? `<button class="btn btn-accent btn-sm" onclick="openBookingModal(${r.id})"><i class="fas fa-calendar-plus"></i> Забронировать</button>` : ''}
                    </div>
                </div>
            </div>`;
        }).join('');
    } catch (err) {
        grid.innerHTML = `<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>${err.message}</p></div>`;
    }
}

// ── Модалка бронирования ─────────────────────────────────────────────────────

async function openBookingModal(roomId) {
    if (!api.isAuth()) { navigate('login'); return; }

    let room, services;
    try {
        [room, services] = await Promise.all([api.getRoom(roomId), api.getServices()]);
    } catch (err) { toast(err.message, 'error'); return; }

    const cat = allCategories.find(c => c.id === room.category_id) || {};
    const today = new Date().toISOString().split('T')[0];
    const tomorrow = new Date(Date.now() + 86400000).toISOString().split('T')[0];

    const svcHtml = services.map(s => `
        <label class="service-check">
            <input type="checkbox" value="${s.id}" data-price="${s.price}">
            ${s.name}
            <span class="service-price">${formatMoney(s.price)}</span>
        </label>
    `).join('');

    openModal(`
        <button class="modal-close" onclick="closeModal()">&times;</button>
        <h3><i class="fas fa-calendar-plus"></i> Бронирование номера ${room.room_number}</h3>
        <p style="color:var(--text-secondary);margin-bottom:16px">${cat.name} &bull; ${formatMoney(cat.base_price)}/ночь &bull; до ${cat.capacity} гостей</p>
        <form id="bookingForm">
            <div class="form-row">
                <div class="form-group">
                    <label>Дата заезда</label>
                    <input type="date" id="bkCheckIn" min="${today}" value="${today}" required onchange="calcBookingTotal()">
                </div>
                <div class="form-group">
                    <label>Дата выезда</label>
                    <input type="date" id="bkCheckOut" min="${tomorrow}" value="${tomorrow}" required onchange="calcBookingTotal()">
                </div>
            </div>
            <div class="form-group">
                <label>Количество гостей</label>
                <input type="number" id="bkGuests" min="1" max="${cat.capacity}" value="1" required>
            </div>
            <div class="form-group">
                <label>Примечания</label>
                <textarea id="bkNotes" rows="2" placeholder="Особые пожелания..."></textarea>
            </div>
            <div class="form-group">
                <label>Дополнительные услуги</label>
                <div class="services-list">${svcHtml}</div>
            </div>
            <div style="background:#E3F2FD;padding:14px;border-radius:8px;margin-bottom:16px;text-align:center">
                <div style="font-size:13px;color:var(--text-secondary)">Итого</div>
                <div id="bookingTotal" style="font-size:24px;font-weight:700;color:var(--primary)">${formatMoney(cat.base_price)}</div>
            </div>
            <input type="hidden" id="bkRoomId" value="${roomId}">
            <input type="hidden" id="bkPrice" value="${cat.base_price}">
            <button type="submit" class="btn btn-primary"><i class="fas fa-check"></i> Подтвердить бронирование</button>
        </form>
    `);

    document.querySelectorAll('.service-check input').forEach(cb => {
        cb.addEventListener('change', calcBookingTotal);
    });

    document.getElementById('bookingForm').onsubmit = submitBooking;
}

function calcBookingTotal() {
    const checkIn = new Date(document.getElementById('bkCheckIn').value);
    const checkOut = new Date(document.getElementById('bkCheckOut').value);
    const price = parseFloat(document.getElementById('bkPrice').value);
    const nights = Math.max(1, Math.round((checkOut - checkIn) / 86400000));

    let svcTotal = 0;
    document.querySelectorAll('.service-check input:checked').forEach(cb => {
        svcTotal += parseFloat(cb.dataset.price);
    });

    const total = nights * price + svcTotal;
    const el = document.getElementById('bookingTotal');
    if (el) el.textContent = formatMoney(total) + ` (${nights} ${nights === 1 ? 'ночь' : nights < 5 ? 'ночи' : 'ночей'})`;
}

async function submitBooking(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type=submit]');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Оформление...';

    const body = {
        room_id: parseInt(document.getElementById('bkRoomId').value),
        check_in_date: document.getElementById('bkCheckIn').value,
        check_out_date: document.getElementById('bkCheckOut').value,
        guests_count: parseInt(document.getElementById('bkGuests').value),
    };
    const notes = document.getElementById('bkNotes').value.trim();
    if (notes) body.notes = notes;

    const selectedServices = [];
    document.querySelectorAll('.service-check input:checked').forEach(cb => {
        selectedServices.push(parseInt(cb.value));
    });
    if (selectedServices.length > 0) body.service_ids = selectedServices;

    try {
        await api.createBooking(body);
        closeModal();
        toast('Бронирование создано!', 'success');
        navigate('my-bookings');
    } catch (err) {
        toast(err.message, 'error');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-check"></i> Подтвердить бронирование';
    }
}

// ── Мои бронирования ─────────────────────────────────────────────────────────

async function renderMyBookings(app) {
    app.innerHTML = `
        <div class="page-header">
            <h1><i class="fas fa-calendar-alt"></i> Мои бронирования</h1>
        </div>
        <div id="bookingsList"><div class="spinner"></div></div>
    `;

    try {
        const bookings = await api.getMyBookings();
        const el = document.getElementById('bookingsList');
        if (!bookings.length) {
            el.innerHTML = `<div class="empty-state card"><i class="fas fa-calendar-times"></i><p>У вас пока нет бронирований</p>
                <br><button class="btn btn-accent" onclick="navigate('rooms')"><i class="fas fa-bed"></i> Перейти к номерам</button></div>`;
            return;
        }
        el.innerHTML = `<div class="card"><div class="table-wrap"><table>
            <thead><tr>
                <th>ID</th><th>Номер</th><th>Заезд</th><th>Выезд</th><th>Гостей</th><th>Сумма</th><th>Статус</th><th>Действия</th>
            </tr></thead>
            <tbody>${bookings.map(b => `<tr>
                <td>#${b.id}</td>
                <td>${b.room_number || b.room_id}</td>
                <td>${formatDate(b.check_in_date)}</td>
                <td>${formatDate(b.check_out_date)}</td>
                <td>${b.guests_count}</td>
                <td><strong>${formatMoney(b.total_amount)}</strong></td>
                <td><span class="status-badge status-${b.status}">${STATUS_LABELS[b.status] || b.status}</span></td>
                <td class="actions-cell">
                    <button class="btn btn-outline btn-sm" onclick="viewBookingDetail(${b.id})" title="Подробнее"><i class="fas fa-eye"></i></button>
                    <button class="btn btn-outline btn-sm" onclick="downloadPdf(${b.id})" title="Скачать PDF"><i class="fas fa-file-pdf"></i></button>
                    ${b.status === 'pending' || b.status === 'confirmed' ? `<button class="btn btn-danger btn-sm" onclick="cancelBookingAction(${b.id})" title="Отменить"><i class="fas fa-times"></i></button>` : ''}
                </td>
            </tr>`).join('')}</tbody>
        </table></div></div>`;
    } catch (err) {
        toast(err.message, 'error');
    }
}

async function viewBookingDetail(id) {
    try {
        const b = await api.getBooking(id);
        openModal(`
            <button class="modal-close" onclick="closeModal()">&times;</button>
            <h3><i class="fas fa-info-circle"></i> Бронирование #${b.id}</h3>
            <div class="booking-detail-grid">
                <div class="detail-item"><label>Номер</label><span>${b.room_number || b.room_id}</span></div>
                <div class="detail-item"><label>Статус</label><span class="status-badge status-${b.status}">${STATUS_LABELS[b.status]}</span></div>
                <div class="detail-item"><label>Заезд</label><span>${formatDate(b.check_in_date)}</span></div>
                <div class="detail-item"><label>Выезд</label><span>${formatDate(b.check_out_date)}</span></div>
                <div class="detail-item"><label>Гостей</label><span>${b.guests_count}</span></div>
                <div class="detail-item"><label>Сумма</label><span style="color:var(--primary);font-weight:700">${formatMoney(b.total_amount)}</span></div>
            </div>
            ${b.notes ? `<p style="color:var(--text-secondary);font-size:13px"><i class="fas fa-sticky-note"></i> ${b.notes}</p>` : ''}
            ${b.services && b.services.length ? `
                <h4 style="margin:16px 0 8px">Дополнительные услуги</h4>
                <table><thead><tr><th>Услуга</th><th>Кол-во</th><th>Цена</th></tr></thead>
                <tbody>${b.services.map(s => `<tr><td>${s.name || s.service_name || s.service_id}</td><td>${s.quantity}</td><td>${formatMoney(s.price || s.price_at_booking)}</td></tr>`).join('')}</tbody></table>
            ` : ''}
            <div style="margin-top:16px;display:flex;gap:8px">
                <button class="btn btn-outline" onclick="downloadPdf(${b.id})"><i class="fas fa-file-pdf"></i> Скачать PDF</button>
                ${b.status === 'pending' || b.status === 'confirmed' ? `<button class="btn btn-danger" onclick="cancelBookingAction(${b.id})"><i class="fas fa-times"></i> Отменить</button>` : ''}
            </div>
        `);
    } catch (err) { toast(err.message, 'error'); }
}

async function downloadPdf(id) {
    try {
        const res = await api.getBookingPdf(id);
        if (!res.ok) throw new Error('Не удалось получить PDF');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `booking_${id}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
        toast('PDF скачан', 'success');
    } catch (err) { toast(err.message, 'error'); }
}

async function cancelBookingAction(id) {
    if (!confirm('Отменить бронирование #' + id + '?')) return;
    try {
        await api.cancelBooking(id);
        toast('Бронирование отменено', 'success');
        closeModal();
        if (currentPage === 'my-bookings') navigate('my-bookings');
        else if (currentPage === 'admin') navigate('admin');
    } catch (err) { toast(err.message, 'error'); }
}

// ── Профиль ──────────────────────────────────────────────────────────────────

async function renderProfile(app) {
    app.innerHTML = '<div class="spinner"></div>';
    try {
        const u = await api.getProfile();
        app.innerHTML = `
        <div class="page-header"><h1><i class="fas fa-user-circle"></i> Личный кабинет</h1></div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
            <div class="card">
                <div class="profile-header">
                    <div class="profile-avatar">${(u.first_name || u.email)[0].toUpperCase()}</div>
                    <div>
                        <h3>${u.first_name || ''} ${u.last_name || ''}</h3>
                        <div style="color:var(--text-secondary)">${u.email}</div>
                        <span class="user-role" style="margin-top:4px;display:inline-block">${ROLE_LABELS[u.role]}</span>
                    </div>
                </div>
                <form id="profileForm">
                    <div class="form-row">
                        <div class="form-group">
                            <label>Имя</label>
                            <input type="text" id="pfFirst" value="${u.first_name || ''}">
                        </div>
                        <div class="form-group">
                            <label>Фамилия</label>
                            <input type="text" id="pfLast" value="${u.last_name || ''}">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Отчество</label>
                        <input type="text" id="pfPatron" value="${u.patronymic || ''}">
                    </div>
                    <div class="form-group">
                        <label>Телефон</label>
                        <input type="tel" id="pfPhone" value="${u.phone || ''}">
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Серия паспорта</label>
                            <input type="text" id="pfPassSer" value="${u.passport_series || ''}" maxlength="4">
                        </div>
                        <div class="form-group">
                            <label>Номер паспорта</label>
                            <input type="text" id="pfPassNum" value="${u.passport_number || ''}" maxlength="6">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Дата рождения</label>
                        <input type="date" id="pfBirth" value="${u.birth_date || ''}">
                    </div>
                    <button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Сохранить изменения</button>
                </form>
            </div>
            <div class="card">
                <h3 class="card-title" style="margin-bottom:16px"><i class="fas fa-key"></i> Смена пароля</h3>
                <form id="passForm">
                    <div class="form-group">
                        <label>Текущий пароль</label>
                        <input type="password" id="pwOld" required>
                    </div>
                    <div class="form-group">
                        <label>Новый пароль</label>
                        <input type="password" id="pwNew" minlength="6" required>
                    </div>
                    <div class="form-group">
                        <label>Подтверждение</label>
                        <input type="password" id="pwNew2" required>
                    </div>
                    <button type="submit" class="btn btn-primary"><i class="fas fa-key"></i> Изменить пароль</button>
                </form>
            </div>
        </div>`;

        document.getElementById('profileForm').onsubmit = async (e) => {
            e.preventDefault();
            try {
                await api.updateProfile({
                    first_name: document.getElementById('pfFirst').value || null,
                    last_name: document.getElementById('pfLast').value || null,
                    patronymic: document.getElementById('pfPatron').value || null,
                    phone: document.getElementById('pfPhone').value || null,
                    passport_series: document.getElementById('pfPassSer').value || null,
                    passport_number: document.getElementById('pfPassNum').value || null,
                    birth_date: document.getElementById('pfBirth').value || null,
                });
                toast('Профиль обновлён', 'success');
            } catch (err) { toast(err.message, 'error'); }
        };

        document.getElementById('passForm').onsubmit = async (e) => {
            e.preventDefault();
            if (document.getElementById('pwNew').value !== document.getElementById('pwNew2').value) {
                toast('Пароли не совпадают', 'error'); return;
            }
            try {
                await api.changePassword({
                    old_password: document.getElementById('pwOld').value,
                    new_password: document.getElementById('pwNew').value,
                });
                toast('Пароль изменён', 'success');
                e.target.reset();
            } catch (err) { toast(err.message, 'error'); }
        };
    } catch (err) { toast(err.message, 'error'); }
}

// ── Админ-панель ─────────────────────────────────────────────────────────────

async function renderAdmin(app) {
    if (!api.isStaff()) { navigate('rooms'); return; }

    app.innerHTML = `
        <div class="page-header"><h1><i class="fas fa-cogs"></i> Панель управления</h1></div>
        <div class="tabs">
            <button class="tab-btn active" onclick="switchAdminTab('bookings')"><i class="fas fa-calendar"></i> Бронирования</button>
            <button class="tab-btn" onclick="switchAdminTab('users')"><i class="fas fa-users"></i> Пользователи</button>
            <button class="tab-btn" onclick="switchAdminTab('reports')"><i class="fas fa-chart-bar"></i> Отчёты</button>
            <button class="tab-btn" onclick="switchAdminTab('audit')"><i class="fas fa-history"></i> Аудит</button>
        </div>
        <div id="adminContent"><div class="spinner"></div></div>
    `;
    await loadAdminBookings();
}

function switchAdminTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    event.target.closest('.tab-btn').classList.add('active');
    const content = document.getElementById('adminContent');
    content.innerHTML = '<div class="spinner"></div>';
    switch (tab) {
        case 'bookings': loadAdminBookings(); break;
        case 'users': loadAdminUsers(); break;
        case 'reports': loadAdminReports(); break;
        case 'audit': loadAdminAudit(); break;
    }
}

async function loadAdminBookings() {
    const el = document.getElementById('adminContent');
    try {
        const bookings = await api.getAllBookings();
        if (!bookings.length) {
            el.innerHTML = '<div class="empty-state card"><i class="fas fa-calendar-times"></i><p>Нет бронирований</p></div>';
            return;
        }
        el.innerHTML = `<div class="card"><div class="table-wrap"><table>
            <thead><tr>
                <th>ID</th><th>Гость</th><th>Номер</th><th>Заезд</th><th>Выезд</th><th>Гостей</th><th>Сумма</th><th>Статус</th><th>Действия</th>
            </tr></thead>
            <tbody>${bookings.map(b => `<tr>
                <td>#${b.id}</td>
                <td>${b.guest_name || b.guest_id}</td>
                <td>${b.room_number || b.room_id}</td>
                <td>${formatDate(b.check_in_date)}</td>
                <td>${formatDate(b.check_out_date)}</td>
                <td>${b.guests_count}</td>
                <td><strong>${formatMoney(b.total_amount)}</strong></td>
                <td><span class="status-badge status-${b.status}">${STATUS_LABELS[b.status] || b.status}</span></td>
                <td class="actions-cell">
                    <button class="btn btn-outline btn-sm" onclick="viewBookingDetail(${b.id})" title="Подробнее"><i class="fas fa-eye"></i></button>
                    <button class="btn btn-outline btn-sm" onclick="downloadPdf(${b.id})" title="PDF"><i class="fas fa-file-pdf"></i></button>
                    ${b.status === 'pending' ? `<button class="btn btn-success btn-sm" onclick="changeStatus(${b.id},'confirmed')" title="Подтвердить"><i class="fas fa-check"></i></button>` : ''}
                    ${b.status === 'confirmed' ? `<button class="btn btn-accent btn-sm" onclick="changeStatus(${b.id},'checked_in')" title="Заселить"><i class="fas fa-door-open"></i></button>` : ''}
                    ${b.status === 'checked_in' ? `<button class="btn btn-outline btn-sm" onclick="changeStatus(${b.id},'checked_out')" title="Выселить"><i class="fas fa-door-closed"></i></button>` : ''}
                    ${['pending','confirmed'].includes(b.status) ? `<button class="btn btn-danger btn-sm" onclick="cancelBookingAction(${b.id})" title="Отменить"><i class="fas fa-times"></i></button>` : ''}
                </td>
            </tr>`).join('')}</tbody>
        </table></div></div>`;
    } catch (err) { el.innerHTML = `<div class="card"><p>${err.message}</p></div>`; }
}

async function changeStatus(id, status) {
    try {
        await api.updateBookingStatus(id, status);
        toast(`Статус бронирования #${id} изменён на "${STATUS_LABELS[status]}"`, 'success');
        await loadAdminBookings();
    } catch (err) { toast(err.message, 'error'); }
}

async function loadAdminUsers() {
    const el = document.getElementById('adminContent');
    try {
        const users = await api.getUsers();
        el.innerHTML = `<div class="card"><div class="table-wrap"><table>
            <thead><tr><th>ID</th><th>Email</th><th>Имя</th><th>Роль</th><th>Статус</th><th>Регистрация</th><th>Действия</th></tr></thead>
            <tbody>${users.map(u => `<tr>
                <td>#${u.id}</td>
                <td>${u.email}</td>
                <td>${u.first_name || ''} ${u.last_name || ''}</td>
                <td><span class="user-role">${ROLE_LABELS[u.role] || u.role}</span></td>
                <td>${u.is_blocked ? '<span class="status-badge status-cancelled">Заблокирован</span>' : '<span class="status-badge status-confirmed">Активен</span>'}</td>
                <td>${formatDate(u.created_at)}</td>
                <td class="actions-cell">
                    ${api.isAdmin() && u.id !== api.user.id ? `
                        <select class="btn btn-outline btn-sm" onchange="changeRole(${u.id}, this.value)" style="padding:4px 8px">
                            <option value="guest" ${u.role==='guest'?'selected':''}>Гость</option>
                            <option value="manager" ${u.role==='manager'?'selected':''}>Менеджер</option>
                            <option value="admin" ${u.role==='admin'?'selected':''}>Админ</option>
                        </select>
                        <button class="btn ${u.is_blocked ? 'btn-success' : 'btn-danger'} btn-sm" onclick="toggleBlock(${u.id}, ${!u.is_blocked})">
                            <i class="fas fa-${u.is_blocked ? 'unlock' : 'ban'}"></i>
                        </button>
                    ` : ''}
                </td>
            </tr>`).join('')}</tbody>
        </table></div></div>`;
    } catch (err) { el.innerHTML = `<div class="card"><p>${err.message}</p></div>`; }
}

async function changeRole(userId, role) {
    try {
        await api.setUserRole(userId, role);
        toast(`Роль пользователя изменена на "${ROLE_LABELS[role]}"`, 'success');
    } catch (err) { toast(err.message, 'error'); await loadAdminUsers(); }
}

async function toggleBlock(userId, blocked) {
    try {
        await api.blockUser(userId, blocked);
        toast(blocked ? 'Пользователь заблокирован' : 'Пользователь разблокирован', 'success');
        await loadAdminUsers();
    } catch (err) { toast(err.message, 'error'); }
}

async function loadAdminReports() {
    const el = document.getElementById('adminContent');
    try {
        const [revenue, occupancy] = await Promise.all([
            api.getRevenue(),
            api.getOccupancy().catch(() => null)
        ]);

        let statsHtml = '';
        if (occupancy) {
            statsHtml = `<div class="stats-grid">
                <div class="stat-card"><i class="fas fa-bed"></i><div class="stat-value">${occupancy.total_rooms || 0}</div><div class="stat-label">Всего номеров</div></div>
                <div class="stat-card"><i class="fas fa-door-open"></i><div class="stat-value">${occupancy.available || 0}</div><div class="stat-label">Свободно</div></div>
                <div class="stat-card"><i class="fas fa-user-check"></i><div class="stat-value">${occupancy.occupied || 0}</div><div class="stat-label">Занято</div></div>
                <div class="stat-card"><i class="fas fa-percentage"></i><div class="stat-value">${occupancy.rate || 0}%</div><div class="stat-label">Загруженность</div></div>
            </div>`;
        }

        el.innerHTML = `
            ${statsHtml}
            <div class="card">
                <h3 class="card-title" style="margin-bottom:16px"><i class="fas fa-chart-line"></i> Доход по категориям</h3>
                <div class="table-wrap"><table>
                    <thead><tr><th>Категория</th><th>Бронирований</th><th>Доход</th></tr></thead>
                    <tbody>${revenue.map(r => `<tr>
                        <td>${r.category || r.category_name || 'Без категории'}</td>
                        <td>${r.bookings_count || r.count || 0}</td>
                        <td><strong>${formatMoney(r.total_revenue || r.revenue || 0)}</strong></td>
                    </tr>`).join('')}</tbody>
                </table></div>
            </div>
        `;
    } catch (err) { el.innerHTML = `<div class="card"><p>${err.message}</p></div>`; }
}

async function loadAdminAudit() {
    const el = document.getElementById('adminContent');
    try {
        const audit = await api.getAudit({ limit: 50 });
        if (!audit.length) {
            el.innerHTML = '<div class="empty-state card"><i class="fas fa-history"></i><p>Нет записей аудита</p></div>';
            return;
        }
        el.innerHTML = `<div class="card">
            <h3 class="card-title" style="margin-bottom:16px"><i class="fas fa-history"></i> Журнал аудита</h3>
            <div class="table-wrap"><table>
                <thead><tr><th>Время</th><th>Таблица</th><th>Операция</th><th>Пользователь</th><th>Подробнее</th></tr></thead>
                <tbody>${audit.map(a => `<tr>
                    <td>${new Date(a.changed_at || a.created_at).toLocaleString('ru-RU')}</td>
                    <td>${a.table_name}</td>
                    <td><span class="status-badge ${(a.action||a.operation) === 'INSERT' ? 'status-confirmed' : (a.action||a.operation) === 'DELETE' ? 'status-cancelled' : 'status-pending'}">${a.action || a.operation}</span></td>
                    <td>${a.changed_by || a.user_id || '—'}</td>
                    <td><button class="btn btn-outline btn-sm" onclick='showAuditDetail(${JSON.stringify(JSON.stringify(a))})'><i class="fas fa-eye"></i></button></td>
                </tr>`).join('')}</tbody>
            </table></div>
        </div>`;
    } catch (err) { el.innerHTML = `<div class="card"><p>${err.message}</p></div>`; }
}

function showAuditDetail(jsonStr) {
    const a = JSON.parse(jsonStr);
    openModal(`
        <button class="modal-close" onclick="closeModal()">&times;</button>
        <h3><i class="fas fa-history"></i> Запись аудита</h3>
        <pre style="background:#F5F5F5;padding:16px;border-radius:8px;font-size:12px;overflow-x:auto;white-space:pre-wrap">${JSON.stringify(a, null, 2)}</pre>
    `);
}

// ── Инициализация ────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('.nav-brand').addEventListener('click', () => {
        navigate(api.isAuth() ? 'rooms' : 'login');
    });
    renderNav();
    navigate(api.isAuth() ? 'rooms' : 'login');
});
