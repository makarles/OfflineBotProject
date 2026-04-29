/**
 * SkyAssist админ-панель.
 * Vanilla JS, три вкладки (Рейс / Борты / Маршруты).
 *
 * Главное:
 * - Вкладка «Рейс» — большая форма с динамическими списками меню и предложений
 * - Вкладки «Борты» и «Маршруты» — таблицы с CRUD через модалки
 * - Все действия дают toast-уведомление
 */

// ===== Состояние =====

let currentFlightData = null;     // последнее загруженное состояние рейса (для reset)
let aircraftList = [];             // справочник для dropdown'а в форме рейса
let routesList = [];               // тот же
let menuItemCounter = 0;           // счётчик для уникальных id строк меню
let offerCounter = 0;              // счётчик для уникальных id строк предложений

// ===== DOM ссылки =====

const $ = (id) => document.getElementById(id);

// ===== API-обёртка =====

async function api(method, path, body = null) {
    const opts = {
        method,
        headers: {'Content-Type': 'application/json'},
    };
    if (body !== null) opts.body = JSON.stringify(body);

    const res = await fetch(path, opts);
    if (res.status === 204) return null;

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        const detail = data.detail;
        // Если detail — объект с errors, делаем структурное исключение
        if (detail && typeof detail === 'object' && detail.errors) {
            const err = new Error(detail.message || 'Ошибка валидации');
            err.errors = detail.errors;
            throw err;
        }
        throw new Error(detail || `${res.status} ${res.statusText}`);
    }
    return data;
}

// ===== Toasts =====

function toast(message, type = 'info', errors = null) {
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = message;

    if (errors && errors.length) {
        const ul = document.createElement('ul');
        ul.className = 'toast-list';
        errors.forEach(e => {
            const li = document.createElement('li');
            li.textContent = e;
            ul.appendChild(li);
        });
        el.appendChild(ul);
    }

    $('toasts').appendChild(el);
    setTimeout(() => el.remove(), errors ? 8000 : 3500);
}

// ===== Вкладки =====

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
});

function switchTab(name) {
    document.querySelectorAll('.tab').forEach(t => {
        t.classList.toggle('active', t.dataset.tab === name);
    });
    document.querySelectorAll('.tab-panel').forEach(p => {
        p.classList.toggle('active', p.id === `panel-${name}`);
    });

    // При переходе на вкладку — обновляем её данные
    if (name === 'aircraft') loadAircraftTable();
    if (name === 'routes') loadRoutesTable();
}

// ===== Вкладка: РЕЙС =====

async function loadFlightData() {
    try {
        // Параллельно тянем все три источника
        const [flightData, aircraft, routes] = await Promise.all([
            api('GET', '/api/admin/flight'),
            api('GET', '/api/admin/aircraft'),
            api('GET', '/api/admin/routes'),
        ]);

        aircraftList = aircraft;
        routesList = routes;
        currentFlightData = flightData;

        fillAircraftSelect();
        fillRoutesSelect();
        fillFlightForm(flightData);
    } catch (err) {
        toast(`Ошибка загрузки данных рейса: ${err.message}`, 'error');
    }
}

function fillAircraftSelect() {
    const select = $('aircraft_id');
    select.innerHTML = '<option value="">— выберите борт —</option>';
    aircraftList.forEach(a => {
        const opt = document.createElement('option');
        opt.value = a.id;
        opt.textContent = `${a.registration} — ${a.aircraft_type}`;
        select.appendChild(opt);
    });
}

function fillRoutesSelect() {
    const select = $('route_id');
    select.innerHTML = '<option value="">— выберите маршрут —</option>';
    routesList.forEach(r => {
        const opt = document.createElement('option');
        opt.value = r.id;
        opt.textContent = `${r.origin_iata} → ${r.destination_iata} (${r.origin_city} — ${r.destination_city})`;
        select.appendChild(opt);
    });
}

function fillFlightForm(data) {
    // Очищаем динамические списки
    $('menu-economy').innerHTML = '';
    $('menu-business').innerHTML = '';
    $('offers-list').innerHTML = '';

    if (!data.flight) {
        // Нет рейса — оставляем пустую форму
        $('meal-type-hint').textContent = '';
        return;
    }

    const f = data.flight;

    // Обычные поля
    $('flight_number').value = f.flight_number || '';
    $('departure_time').value = f.departure_time || '';
    $('arrival_time').value = f.arrival_time || '';
    $('aircraft_id').value = f.aircraft_id || '';
    $('route_id').value = f.route_id || '';
    $('cruising_altitude').value = f.cruising_altitude ?? '';
    $('cruising_speed').value = f.cruising_speed ?? '';
    $('meal_type').value = f.meal_type || 'full';

    $('return_flight_number').value = f.return_flight_number || '';
    $('return_departure_time').value = f.return_departure_time || '';
    $('return_arrival_time').value = f.return_arrival_time || '';

    $('weather_description_ru').value = f.weather_description_ru || '';
    $('weather_description_en').value = f.weather_description_en || '';
    $('weather_temp_celsius').value = f.weather_temp_celsius ?? '';

    $('exchange_rate_currency').value = f.exchange_rate_currency || '';
    $('exchange_rate_to_rub').value = f.exchange_rate_to_rub ?? '';
    $('exchange_rate_note_ru').value = f.exchange_rate_note_ru || '';
    $('exchange_rate_note_en').value = f.exchange_rate_note_en || '';

    // Меню
    data.menu_items.forEach(m => addMenuRow(m.cabin_class, m));

    // Предложения
    data.commercial_offers.forEach(o => addOfferRow(o));

    updateMealTypeHint();
}

function addMenuRow(cabinClass, data = null) {
    const id = `menu-${menuItemCounter++}`;
    const container = $(`menu-${cabinClass}`);

    const row = document.createElement('div');
    row.className = 'menu-row';
    row.dataset.menuId = id;
    row.dataset.cabinClass = cabinClass;

    row.innerHTML = `
        <button type="button" class="delete-btn" title="Удалить">×</button>

        <div class="grid-2">
            <div class="field">
                <label>Название (RU) *</label>
                <input type="text" class="m-name_ru" maxlength="200" required>
            </div>
            <div class="field">
                <label>Название (EN)</label>
                <input type="text" class="m-name_en" maxlength="200">
            </div>
        </div>

        <div class="grid-2">
            <div class="field">
                <label>Описание (RU)</label>
                <input type="text" class="m-description_ru" maxlength="500">
            </div>
            <div class="field">
                <label>Описание (EN)</label>
                <input type="text" class="m-description_en" maxlength="500">
            </div>
        </div>

        <div class="grid-3">
            <div class="field">
                <label>Категория</label>
                <select class="m-category">
                    <option value="main">Основное блюдо</option>
                    <option value="starter">Закуска</option>
                    <option value="dessert">Десерт</option>
                    <option value="drink">Напиток</option>
                    <option value="snack">Снэк/сэндвич</option>
                </select>
            </div>
            <div class="field">
                <label>Цена, руб (0 = включено)</label>
                <input type="number" step="0.01" class="m-price" value="0">
            </div>
            <div class="field checkbox-field">
                <label>
                    <input type="checkbox" class="m-is_vegetarian">
                    Вегетарианское
                </label>
            </div>
        </div>
    `;

    // Заполнение значениями
    if (data) {
        row.querySelector('.m-name_ru').value = data.name_ru || '';
        row.querySelector('.m-name_en').value = data.name_en || '';
        row.querySelector('.m-description_ru').value = data.description_ru || '';
        row.querySelector('.m-description_en').value = data.description_en || '';
        row.querySelector('.m-category').value = data.category || 'main';
        row.querySelector('.m-price').value = data.price ?? 0;
        row.querySelector('.m-is_vegetarian').checked = !!data.is_vegetarian;
    }

    row.querySelector('.delete-btn').addEventListener('click', () => row.remove());

    container.appendChild(row);
}

function addOfferRow(data = null) {
    const id = `offer-${offerCounter++}`;
    const container = $('offers-list');

    const row = document.createElement('div');
    row.className = 'menu-row';
    row.dataset.offerId = id;

    row.innerHTML = `
        <button type="button" class="delete-btn" title="Удалить">×</button>

        <div class="grid-2">
            <div class="field">
                <label>Заголовок (RU) *</label>
                <input type="text" class="o-title_ru" maxlength="200" required>
            </div>
            <div class="field">
                <label>Заголовок (EN)</label>
                <input type="text" class="o-title_en" maxlength="200">
            </div>
        </div>

        <div class="grid-2">
            <div class="field">
                <label>Описание (RU)</label>
                <input type="text" class="o-description_ru" maxlength="500">
            </div>
            <div class="field">
                <label>Описание (EN)</label>
                <input type="text" class="o-description_en" maxlength="500">
            </div>
        </div>

        <div class="field">
            <label>Категория</label>
            <input type="text" class="o-category" maxlength="50" placeholder="transfer / hotel / shopping">
        </div>
    `;

    if (data) {
        row.querySelector('.o-title_ru').value = data.title_ru || '';
        row.querySelector('.o-title_en').value = data.title_en || '';
        row.querySelector('.o-description_ru').value = data.description_ru || '';
        row.querySelector('.o-description_en').value = data.description_en || '';
        row.querySelector('.o-category').value = data.category || '';
    }

    row.querySelector('.delete-btn').addEventListener('click', () => row.remove());
    container.appendChild(row);
}

document.querySelectorAll('.btn-add[data-class]').forEach(btn => {
    btn.addEventListener('click', () => addMenuRow(btn.dataset.class));
});

$('btn-add-offer').addEventListener('click', () => addOfferRow());

$('reload-flight-btn').addEventListener('click', () => {
    loadFlightData();
    toast('Изменения сброшены', 'info');
});

// При выборе route — подсказываем meal_type
$('route_id').addEventListener('change', async () => {
    const routeId = $('route_id').value;
    if (!routeId) {
        $('meal-type-hint').textContent = '';
        return;
    }
    try {
        const data = await api('GET', `/api/admin/flight/suggest-meal-type?route_id=${routeId}`);
        const labelMap = {
            'full': 'полный приём пищи',
            'light': 'лёгкий перекус',
            'snack_only': 'только снэки',
            'no_meal': 'без питания',
        };
        $('meal-type-hint').textContent =
            `Длительность рейса ${data.duration_min} мин — рекомендуется «${labelMap[data.meal_type]}»`;

        // Если пользователь не трогал meal_type — подставим автоматически
        // (только если поле в дефолтном состоянии — для UX-простоты не трогаем)
    } catch (err) {
        $('meal-type-hint').textContent = '';
    }
});

// Сборка payload и отправка PUT /flight
$('flight-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const payload = {
        flight_number: $('flight_number').value.trim(),
        departure_time: $('departure_time').value.trim(),
        arrival_time: $('arrival_time').value.trim(),
        aircraft_id: parseInt($('aircraft_id').value, 10),
        route_id: parseInt($('route_id').value, 10),
        cruising_altitude: parseIntOrNull($('cruising_altitude').value),
        cruising_speed: parseIntOrNull($('cruising_speed').value),
        meal_type: $('meal_type').value,

        return_flight_number: $('return_flight_number').value.trim() || null,
        return_departure_time: $('return_departure_time').value.trim() || null,
        return_arrival_time: $('return_arrival_time').value.trim() || null,

        weather_description_ru: $('weather_description_ru').value.trim() || null,
        weather_description_en: $('weather_description_en').value.trim() || null,
        weather_temp_celsius: parseIntOrNull($('weather_temp_celsius').value),

        exchange_rate_currency: $('exchange_rate_currency').value.trim() || null,
        exchange_rate_to_rub: parseFloatOrNull($('exchange_rate_to_rub').value),
        exchange_rate_note_ru: $('exchange_rate_note_ru').value.trim() || null,
        exchange_rate_note_en: $('exchange_rate_note_en').value.trim() || null,

        menu_items: collectMenuItems(),
        commercial_offers: collectOffers(),
    };

    if (!payload.aircraft_id || !payload.route_id) {
        toast('Выберите борт и маршрут', 'error');
        return;
    }

    const btn = $('save-flight-btn');
    btn.disabled = true;
    btn.textContent = 'Сохранение...';
    try {
        await api('PUT', '/api/admin/flight', payload);
        toast('Рейс сохранён и применён', 'success');
        loadFlightData();  // перезагружаем данные с свежими id'шниками
    } catch (err) {
        toast(err.message, 'error', err.errors);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Сохранить и применить';
    }
});

function collectMenuItems() {
    const items = [];
    document.querySelectorAll('.menu-row[data-menu-id]').forEach(row => {
        items.push({
            name_ru: row.querySelector('.m-name_ru').value.trim(),
            name_en: row.querySelector('.m-name_en').value.trim() || null,
            description_ru: row.querySelector('.m-description_ru').value.trim() || null,
            description_en: row.querySelector('.m-description_en').value.trim() || null,
            category: row.querySelector('.m-category').value,
            cabin_class: row.dataset.cabinClass,
            is_vegetarian: row.querySelector('.m-is_vegetarian').checked,
            price: parseFloat(row.querySelector('.m-price').value) || 0,
        });
    });
    return items;
}

function collectOffers() {
    const offers = [];
    document.querySelectorAll('.menu-row[data-offer-id]').forEach(row => {
        offers.push({
            title_ru: row.querySelector('.o-title_ru').value.trim(),
            title_en: row.querySelector('.o-title_en').value.trim() || null,
            description_ru: row.querySelector('.o-description_ru').value.trim() || null,
            description_en: row.querySelector('.o-description_en').value.trim() || null,
            category: row.querySelector('.o-category').value.trim() || null,
        });
    });
    return offers;
}

function parseIntOrNull(value) {
    if (value === '' || value == null) return null;
    const n = parseInt(value, 10);
    return isNaN(n) ? null : n;
}

function parseFloatOrNull(value) {
    if (value === '' || value == null) return null;
    const n = parseFloat(value);
    return isNaN(n) ? null : n;
}

function updateMealTypeHint() {
    // Триггерим обновление подсказки если route уже выбран
    const evt = new Event('change');
    $('route_id').dispatchEvent(evt);
}

// ===== Вкладка: БОРТЫ =====

async function loadAircraftTable() {
    try {
        aircraftList = await api('GET', '/api/admin/aircraft');
        renderAircraftTable();
    } catch (err) {
        toast(`Ошибка загрузки бортов: ${err.message}`, 'error');
    }
}

function renderAircraftTable() {
    const tbody = $('aircraft-table-body');

    if (!aircraftList.length) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty">Нет бортов. Добавьте первый.</td></tr>';
        return;
    }

    tbody.innerHTML = aircraftList.map(a => `
        <tr>
            <td><strong>${escapeHtml(a.registration)}</strong></td>
            <td>${escapeHtml(a.aircraft_type)}</td>
            <td>${escapeHtml(a.manufacturer || '—')}</td>
            <td>${a.capacity_economy ?? '—'}</td>
            <td>${a.capacity_business ?? '—'}</td>
            <td>${a.year_manufactured ?? '—'}</td>
            <td><span class="status-badge ${a.status}">${a.status === 'active' ? 'Активный' : 'Обслуживание'}</span></td>
            <td class="actions">
                <button class="btn-icon" data-edit-aircraft="${a.id}">Изм.</button>
                <button class="btn-icon danger" data-delete-aircraft="${a.id}">Удал.</button>
            </td>
        </tr>
    `).join('');

    tbody.querySelectorAll('[data-edit-aircraft]').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = parseInt(btn.dataset.editAircraft, 10);
            const a = aircraftList.find(x => x.id === id);
            openAircraftModal(a);
        });
    });

    tbody.querySelectorAll('[data-delete-aircraft]').forEach(btn => {
        btn.addEventListener('click', () => deleteAircraft(parseInt(btn.dataset.deleteAircraft, 10)));
    });
}

$('btn-add-aircraft').addEventListener('click', () => openAircraftModal(null));

function openAircraftModal(data) {
    $('aircraft-modal-title').textContent = data ? 'Редактировать борт' : 'Добавить борт';
    $('aircraft-id').value = data?.id || '';
    $('ac-registration').value = data?.registration || '';
    $('ac-aircraft_type').value = data?.aircraft_type || '';
    $('ac-manufacturer').value = data?.manufacturer || '';
    $('ac-capacity_economy').value = data?.capacity_economy ?? '';
    $('ac-capacity_business').value = data?.capacity_business ?? '';
    $('ac-year_manufactured').value = data?.year_manufactured ?? '';
    $('ac-status').value = data?.status || 'active';

    $('aircraft-modal').hidden = false;
    setTimeout(() => $('ac-registration').focus(), 50);
}

function closeAircraftModal() {
    $('aircraft-modal').hidden = true;
}

$('aircraft-cancel').addEventListener('click', closeAircraftModal);
$('aircraft-modal').addEventListener('click', (e) => {
    if (e.target === $('aircraft-modal')) closeAircraftModal();
});

$('aircraft-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = $('aircraft-id').value;
    const payload = {
        registration: $('ac-registration').value.trim(),
        aircraft_type: $('ac-aircraft_type').value.trim(),
        manufacturer: $('ac-manufacturer').value.trim() || null,
        capacity_economy: parseIntOrNull($('ac-capacity_economy').value),
        capacity_business: parseIntOrNull($('ac-capacity_business').value),
        year_manufactured: parseIntOrNull($('ac-year_manufactured').value),
        status: $('ac-status').value,
    };

    try {
        if (id) {
            await api('PUT', `/api/admin/aircraft/${id}`, payload);
            toast(`Борт ${payload.registration} обновлён`, 'success');
        } else {
            await api('POST', '/api/admin/aircraft', payload);
            toast(`Борт ${payload.registration} добавлен`, 'success');
        }
        closeAircraftModal();
        loadAircraftTable();
    } catch (err) {
        toast(err.message, 'error');
    }
});

async function deleteAircraft(id) {
    const a = aircraftList.find(x => x.id === id);
    if (!confirm(`Удалить борт ${a.registration}?`)) return;
    try {
        await api('DELETE', `/api/admin/aircraft/${id}`);
        toast(`Борт ${a.registration} удалён`, 'success');
        loadAircraftTable();
    } catch (err) {
        toast(err.message, 'error');
    }
}

// ===== Вкладка: МАРШРУТЫ =====

async function loadRoutesTable() {
    try {
        routesList = await api('GET', '/api/admin/routes');
        renderRoutesTable();
    } catch (err) {
        toast(`Ошибка загрузки маршрутов: ${err.message}`, 'error');
    }
}

function renderRoutesTable() {
    const tbody = $('routes-table-body');

    if (!routesList.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty">Нет маршрутов. Добавьте первый.</td></tr>';
        return;
    }

    tbody.innerHTML = routesList.map(r => `
        <tr>
            <td><strong>${escapeHtml(r.origin_iata)}</strong> ${escapeHtml(r.origin_city)}</td>
            <td><strong>${escapeHtml(r.destination_iata)}</strong> ${escapeHtml(r.destination_city)}</td>
            <td>${r.is_domestic ? 'Внутренний' : 'Международный'}</td>
            <td>${r.flight_duration_min ?? '—'}</td>
            <td>${r.distance_km ?? '—'}</td>
            <td class="actions">
                <button class="btn-icon" data-edit-route="${r.id}">Изм.</button>
                <button class="btn-icon danger" data-delete-route="${r.id}">Удал.</button>
            </td>
        </tr>
    `).join('');

    tbody.querySelectorAll('[data-edit-route]').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = parseInt(btn.dataset.editRoute, 10);
            const r = routesList.find(x => x.id === id);
            openRouteModal(r);
        });
    });

    tbody.querySelectorAll('[data-delete-route]').forEach(btn => {
        btn.addEventListener('click', () => deleteRoute(parseInt(btn.dataset.deleteRoute, 10)));
    });
}

$('btn-add-route').addEventListener('click', () => openRouteModal(null));

function openRouteModal(data) {
    $('route-modal-title').textContent = data ? 'Редактировать маршрут' : 'Добавить маршрут';
    $('route-id').value = data?.id || '';
    $('rt-origin_city').value = data?.origin_city || '';
    $('rt-origin_iata').value = data?.origin_iata || '';
    $('rt-origin_country').value = data?.origin_country || '';
    $('rt-destination_city').value = data?.destination_city || '';
    $('rt-destination_iata').value = data?.destination_iata || '';
    $('rt-destination_country').value = data?.destination_country || '';
    $('rt-is_domestic').checked = !!data?.is_domestic;
    $('rt-flight_duration_min').value = data?.flight_duration_min ?? '';
    $('rt-distance_km').value = data?.distance_km ?? '';

    $('route-modal').hidden = false;
    setTimeout(() => $('rt-origin_city').focus(), 50);
}

function closeRouteModal() {
    $('route-modal').hidden = true;
}

$('route-cancel').addEventListener('click', closeRouteModal);
$('route-modal').addEventListener('click', (e) => {
    if (e.target === $('route-modal')) closeRouteModal();
});

$('route-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = $('route-id').value;
    const payload = {
        origin_city: $('rt-origin_city').value.trim(),
        origin_iata: $('rt-origin_iata').value.trim().toUpperCase(),
        origin_country: $('rt-origin_country').value.trim() || null,
        destination_city: $('rt-destination_city').value.trim(),
        destination_iata: $('rt-destination_iata').value.trim().toUpperCase(),
        destination_country: $('rt-destination_country').value.trim() || null,
        is_domestic: $('rt-is_domestic').checked,
        flight_duration_min: parseIntOrNull($('rt-flight_duration_min').value),
        distance_km: parseIntOrNull($('rt-distance_km').value),
    };

    try {
        if (id) {
            await api('PUT', `/api/admin/routes/${id}`, payload);
            toast(`Маршрут ${payload.origin_iata}→${payload.destination_iata} обновлён`, 'success');
        } else {
            await api('POST', '/api/admin/routes', payload);
            toast(`Маршрут ${payload.origin_iata}→${payload.destination_iata} добавлен`, 'success');
        }
        closeRouteModal();
        loadRoutesTable();
    } catch (err) {
        toast(err.message, 'error');
    }
});

async function deleteRoute(id) {
    const r = routesList.find(x => x.id === id);
    if (!confirm(`Удалить маршрут ${r.origin_iata}→${r.destination_iata}?`)) return;
    try {
        await api('DELETE', `/api/admin/routes/${id}`);
        toast(`Маршрут ${r.origin_iata}→${r.destination_iata} удалён`, 'success');
        loadRoutesTable();
    } catch (err) {
        toast(err.message, 'error');
    }
}

// ===== Утилиты =====

function escapeHtml(s) {
    if (s == null) return '';
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
}

// ===== Инициализация =====

loadFlightData();
