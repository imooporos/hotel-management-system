/* =============================================================================
   api.js — HTTP-клиент для взаимодействия с FastAPI бэкендом
   ============================================================================= */

const API_BASE = window.location.origin + '/api';

class HotelAPI {
    constructor() {
        this.token = localStorage.getItem('hotel_token');
        this.user = JSON.parse(localStorage.getItem('hotel_user') || 'null');
    }

    get headers() {
        const h = { 'Content-Type': 'application/json' };
        if (this.token) h['Authorization'] = `Bearer ${this.token}`;
        return h;
    }

    setAuth(data) {
        this.token = data.access_token;
        this.user = { id: data.user_id, email: data.email, role: data.role };
        localStorage.setItem('hotel_token', this.token);
        localStorage.setItem('hotel_user', JSON.stringify(this.user));
    }

    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('hotel_token');
        localStorage.removeItem('hotel_user');
    }

    isAuth() { return !!this.token; }
    isAdmin() { return this.user?.role === 'admin'; }
    isManager() { return this.user?.role === 'manager'; }
    isStaff() { return this.isAdmin() || this.isManager(); }

    async request(method, path, body = null) {
        const opts = { method, headers: this.headers };
        if (body) opts.body = JSON.stringify(body);
        const res = await fetch(API_BASE + path, opts);
        if (res.status === 401) {
            this.logout();
            window.location.reload();
            throw new Error('Сессия истекла');
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Ошибка ${res.status}`);
        }
        if (res.status === 204) return null;
        const ct = res.headers.get('content-type') || '';
        if (ct.includes('application/json')) return res.json();
        return res;
    }

    // ── Авторизация ──────────────────────────────────────────────
    login(email, password) {
        return this.request('POST', '/auth/login', { email, password });
    }

    register(data) {
        return this.request('POST', '/auth/register', data);
    }

    // ── Пользователи ─────────────────────────────────────────────
    getProfile() { return this.request('GET', '/users/me'); }

    updateProfile(data) { return this.request('PUT', '/users/me', data); }

    changePassword(data) { return this.request('PUT', '/users/me/password', data); }

    getUsers() { return this.request('GET', '/users/'); }

    setUserRole(userId, role) {
        return this.request('PUT', `/users/${userId}/role`, { role });
    }

    blockUser(userId, blocked) {
        return this.request('PUT', `/users/${userId}/block`, { is_blocked: blocked });
    }

    // ── Номера ───────────────────────────────────────────────────
    getRooms(params = {}) {
        const qs = new URLSearchParams(params).toString();
        return this.request('GET', '/rooms/' + (qs ? '?' + qs : ''));
    }

    getRoom(id) { return this.request('GET', `/rooms/${id}`); }

    getCategories() { return this.request('GET', '/rooms/categories'); }

    getRoomAmenities(id) { return this.request('GET', `/rooms/${id}/amenities`); }

    // ── Бронирования ─────────────────────────────────────────────
    createBooking(data) { return this.request('POST', '/bookings/', data); }

    getMyBookings() { return this.request('GET', '/bookings/my'); }

    getAllBookings() { return this.request('GET', '/bookings/all'); }

    getBooking(id) { return this.request('GET', `/bookings/${id}`); }

    cancelBooking(id) { return this.request('PUT', `/bookings/${id}/cancel`); }

    updateBookingStatus(id, status) {
        return this.request('PUT', `/bookings/${id}/status`, { status });
    }

    addBookingService(bookingId, serviceId, quantity) {
        return this.request('POST', `/bookings/${bookingId}/services`, {
            service_id: serviceId, quantity
        });
    }

    getBookingPdf(id) {
        return fetch(API_BASE + `/reports/booking/${id}/pdf`, { headers: this.headers });
    }

    // ── Услуги ───────────────────────────────────────────────────
    getServices() { return this.request('GET', '/services/'); }

    getAllServices() { return this.request('GET', '/services/all'); }

    // ── Отчёты ───────────────────────────────────────────────────
    getRevenue(params = {}) {
        const qs = new URLSearchParams(params).toString();
        return this.request('GET', '/reports/revenue' + (qs ? '?' + qs : ''));
    }

    getOccupancy() { return this.request('GET', '/reports/occupancy'); }

    getAudit(params = {}) {
        const qs = new URLSearchParams(params).toString();
        return this.request('GET', '/reports/audit' + (qs ? '?' + qs : ''));
    }
}

const api = new HotelAPI();
