let currentFlightData = null;
let aircraftList = [];
let routesList = [];
let offerCounter = 0;

const $ = (id) => document.getElementById(id);

function getValue(...ids) {
    for (const id of ids) {
        const el = $(id);
        if (el) {
            return el.value.trim();
        }
    }

    return '';
}

function setValue(id, value) {
    const el = $(id);
    if (el) {
        el.value = value ?? '';
    }
}

async function api(method, path, body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };

    if (body !== null) {
        opts.body = JSON.stringify(body);
    }

    const res = await fetch(path, opts);

    if (res.status === 204) {
        return null;
    }

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
        const detail = data.detail;

        if (detail && typeof detail === 'object' && detail.errors) {
            const err = new Error(detail.message || 'Ошибка валидации');
            err.errors = detail.errors;
            throw err;
        }

        throw new Error(typeof detail === 'string' ? detail : `${res.status} ${res.statusText}`);
    }

    return data;
}

function toast(message, type = 'info', errors = null) {
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = message;

    if (errors && errors.length) {
        const ul = document.createElement('ul');
        ul.className = 'toast-list';

        errors.forEach(error => {
            const li = document.createElement('li');
            li.textContent = error;
            ul.appendChild(li);
        });

        el.appendChild(ul);
    }

    $('toasts').appendChild(el);
    setTimeout(() => el.remove(), errors ? 8000 : 3500);
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function parseIntOrNull(value) {
    if (value === '' || value == null) {
        return null;
    }

    const number = parseInt(value, 10);
    return Number.isNaN(number) ? null : number;
}

function parseFloatOrNull(value) {
    if (value === '' || value == null) {
        return null;
    }

    const number = parseFloat(value);
    return Number.isNaN(number) ? null : number;
}

function switchTab(name) {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === name);
    });

    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `panel-${name}`);
    });

    if (name === 'aircraft') {
        loadAircraftTable();
    }

    if (name === 'routes') {
        loadRoutesTable();
    }
}

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
});

async function loadFlightData() {
    try {
        const [flightData, aircraft, routes] = await Promise.all([
            api('GET', '/api/admin/flight'),
            api('GET', '/api/admin/aircraft'),
            api('GET', '/api/admin/routes'),
        ]);

        currentFlightData = flightData;
        aircraftList = aircraft || [];
        routesList = routes || [];

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

    aircraftList.forEach(aircraft => {
        const option = document.createElement('option');
        option.value = aircraft.id;
        option.textContent = `${aircraft.registration} — ${aircraft.aircraft_type}`;
        select.appendChild(option);
    });
}

function fillRoutesSelect() {
    const select = $('route_id');

    select.innerHTML = '<option value="">— выберите маршрут —</option>';

    routesList.forEach(route => {
        const option = document.createElement('option');
        option.value = route.id;

        const routeType = route.is_domestic ? 'внутренний' : 'международный';
        option.textContent = `${route.origin_iata} → ${route.destination_iata} (${route.origin_city} — ${route.destination_city}, ${routeType})`;

        select.appendChild(option);
    });
}

function getSelectedRoute() {
    const routeId = parseInt($('route_id').value, 10);

    if (!routeId) {
        return null;
    }

    return routesList.find(route => Number(route.id) === routeId) || null;
}

function isSelectedRouteDomestic() {
    const route = getSelectedRoute();

    if (!route) {
        return false;
    }

    return Boolean(route.is_domestic);
}

function setExchangeFieldsDisabled(disabled) {
    $('exchange_rate_currency').disabled = disabled;
    $('exchange_rate_to_rub').disabled = disabled;
    $('exchange_rate_note_ru').disabled = disabled;
    $('exchange_rate_note_en').disabled = disabled;
}

function clearExchangeFields() {
    $('exchange_rate_currency').value = '';
    $('exchange_rate_to_rub').value = '';
    $('exchange_rate_note_ru').value = '';
    $('exchange_rate_note_en').value = '';
}

function updateExchangeRateState() {
    const route = getSelectedRoute();
    const card = $('exchange-rate-card');
    const hint = $('exchange-rate-hint');

    if (!card || !hint) {
        return;
    }

    if (!route) {
        card.classList.remove('muted-card');
        setExchangeFieldsDisabled(false);
        hint.textContent = 'Для внутренних рейсов курс валюты можно не заполнять.';
        return;
    }

    if (Boolean(route.is_domestic)) {
        card.classList.add('muted-card');
        clearExchangeFields();
        setExchangeFieldsDisabled(true);
        hint.textContent = 'Выбран внутренний рейс. Курс валюты будет очищен и не будет использоваться.';
        return;
    }

    card.classList.remove('muted-card');
    setExchangeFieldsDisabled(false);
    hint.textContent = 'Для международного рейса можно указать валюту пункта назначения и курс к рублю.';
}

function clearMenuTextareas() {
    setValue('menu_economy_text_ru', '');
    setValue('menu_economy_text_en', '');
    setValue('menu_business_text_ru', '');
    setValue('menu_business_text_en', '');

    // совместимость со старой версией HTML
    setValue('menu_economy_text', '');
    setValue('menu_business_text', '');
}

function fillFlightForm(data) {
    clearMenuTextareas();
    $('offers-list').innerHTML = '';

    if (!data || !data.flight) {
        $('meal-type-hint').textContent = '';
        updateExchangeRateState();
        return;
    }

    const f = data.flight;

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

    fillMenuTextareas(data.menu_items || []);

    (data.commercial_offers || []).forEach(offer => addOfferRow(offer));

    updateExchangeRateState();
    updateMealTypeHint();
}

function fillMenuTextareas(menuItems) {
    const economyRu = [];
    const economyEn = [];
    const businessRu = [];
    const businessEn = [];

    menuItems.forEach(item => {
        const ruName = item.name_ru || '';
        const enName = item.name_en || '';
        const ruDescription = item.description_ru || '';
        const enDescription = item.description_en || '';

        let textRu = '';
        let textEn = '';

        if (
            ruDescription
            && ruName
            && ruName !== 'Меню эконом-класса'
            && ruName !== 'Меню бизнес-класса'
        ) {
            textRu = `${ruName}: ${ruDescription}`;
        } else {
            textRu = ruDescription || ruName;
        }

        if (
            enDescription
            && enName
            && enName !== 'Economy class menu'
            && enName !== 'Business class menu'
        ) {
            textEn = `${enName}: ${enDescription}`;
        } else {
            textEn = enDescription || enName;
        }

        if (item.cabin_class === 'business') {
            if (textRu) {
                businessRu.push(textRu);
            }

            if (textEn) {
                businessEn.push(textEn);
            }
        } else {
            if (textRu) {
                economyRu.push(textRu);
            }

            if (textEn) {
                economyEn.push(textEn);
            }
        }
    });

    setValue('menu_economy_text_ru', economyRu.join('\n'));
    setValue('menu_economy_text_en', economyEn.join('\n'));
    setValue('menu_business_text_ru', businessRu.join('\n'));
    setValue('menu_business_text_en', businessEn.join('\n'));

    // совместимость со старой версией HTML
    setValue('menu_economy_text', economyRu.join('\n'));
    setValue('menu_business_text', businessRu.join('\n'));
}

function collectMenuItems() {
    const items = [];

    const economyTextRu = getValue('menu_economy_text_ru', 'menu_economy_text');
    const economyTextEn = getValue('menu_economy_text_en');
    const businessTextRu = getValue('menu_business_text_ru', 'menu_business_text');
    const businessTextEn = getValue('menu_business_text_en');

    if (economyTextRu || economyTextEn) {
        items.push({
            name_ru: 'Меню эконом-класса',
            name_en: 'Economy class menu',
            description_ru: economyTextRu || null,
            description_en: economyTextEn || null,
            category: 'main',
            cabin_class: 'economy',
            is_vegetarian: false,
            price: 0,
        });
    }

    if (businessTextRu || businessTextEn) {
        items.push({
            name_ru: 'Меню бизнес-класса',
            name_en: 'Business class menu',
            description_ru: businessTextRu || null,
            description_en: businessTextEn || null,
            category: 'main',
            cabin_class: 'business',
            is_vegetarian: false,
            price: 0,
        });
    }

    return items;
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

function collectOffers() {
    const offers = [];

    document.querySelectorAll('.menu-row[data-offer-id]').forEach(row => {
        const titleRu = row.querySelector('.o-title_ru').value.trim();

        if (!titleRu) {
            return;
        }

        offers.push({
            title_ru: titleRu,
            title_en: row.querySelector('.o-title_en').value.trim() || null,
            description_ru: row.querySelector('.o-description_ru').value.trim() || null,
            description_en: row.querySelector('.o-description_en').value.trim() || null,
            category: row.querySelector('.o-category').value.trim() || null,
        });
    });

    return offers;
}

async function updateMealTypeHint() {
    const routeId = $('route_id').value;

    if (!routeId) {
        $('meal-type-hint').textContent = '';
        return;
    }

    try {
        const data = await api('GET', `/api/admin/flight/suggest-meal-type?route_id=${routeId}`);

        const labelMap = {
            full: 'полный приём пищи',
            light: 'лёгкий перекус',
            snack_only: 'только снэки',
            no_meal: 'без питания',
        };

        $('meal-type-hint').textContent =
            `Длительность рейса ${data.duration_min} мин — рекомендуется «${labelMap[data.meal_type] || data.meal_type}»`;
    } catch (err) {
        $('meal-type-hint').textContent = '';
    }
}

$('route_id').addEventListener('change', () => {
    updateExchangeRateState();
    updateMealTypeHint();
});

$('btn-add-offer').addEventListener('click', () => addOfferRow());

$('reload-flight-btn').addEventListener('click', () => {
    loadFlightData();
    toast('Изменения сброшены', 'info');
});

$('sync-aircraft-btn').addEventListener('click', async () => {
    const confirmed = confirm(
        'Передать сохранённые данные рейса на бортовой сервер самолёта?\n\n' +
        'Передаются только уже сохранённые данные. Если вы меняли форму, сначала нажмите «Сохранить и применить».'
    );

    if (!confirmed) {
        return;
    }

    const btn = $('sync-aircraft-btn');
    btn.disabled = true;
    btn.textContent = 'Передача...';

    try {
        const result = await api('POST', '/api/sync/push-to-aircraft');
        toast(result.message || 'Данные переданы на бортовой сервер', 'success');
    } catch (err) {
        toast(err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Передать данные на бортовой сервер';
    }
});

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

    if (isSelectedRouteDomestic()) {
        payload.exchange_rate_currency = null;
        payload.exchange_rate_to_rub = null;
        payload.exchange_rate_note_ru = null;
        payload.exchange_rate_note_en = null;
    }

    const btn = $('save-flight-btn');
    btn.disabled = true;
    btn.textContent = 'Сохранение...';

    try {
        await api('PUT', '/api/admin/flight', payload);
        toast('Рейс сохранён и применён', 'success');
        await loadFlightData();
    } catch (err) {
        toast(err.message, 'error', err.errors);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Сохранить и применить';
    }
});

async function loadAircraftTable() {
    try {
        aircraftList = await api('GET', '/api/admin/aircraft');
        renderAircraftTable();
        fillAircraftSelect();
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

    tbody.innerHTML = aircraftList.map(aircraft => `
        <tr>
            <td><strong>${escapeHtml(aircraft.registration)}</strong></td>
            <td>${escapeHtml(aircraft.aircraft_type)}</td>
            <td>${escapeHtml(aircraft.manufacturer || '—')}</td>
            <td>${aircraft.capacity_economy ?? '—'}</td>
            <td>${aircraft.capacity_business ?? '—'}</td>
            <td>${aircraft.year_manufactured ?? '—'}</td>
            <td>
                <span class="status-badge ${escapeHtml(aircraft.status)}">
                    ${aircraft.status === 'active' ? 'Активный' : 'Обслуживание'}
                </span>
            </td>
            <td class="actions">
                <button class="btn-icon" data-edit-aircraft="${aircraft.id}">Изм.</button>
                <button class="btn-icon danger" data-delete-aircraft="${aircraft.id}">Удал.</button>
            </td>
        </tr>
    `).join('');

    tbody.querySelectorAll('[data-edit-aircraft]').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = parseInt(btn.dataset.editAircraft, 10);
            const aircraft = aircraftList.find(item => item.id === id);
            openAircraftModal(aircraft);
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
    if (e.target === $('aircraft-modal')) {
        closeAircraftModal();
    }
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
        await loadAircraftTable();
        await loadFlightData();
    } catch (err) {
        toast(err.message, 'error');
    }
});

async function deleteAircraft(id) {
    const aircraft = aircraftList.find(item => item.id === id);

    if (!aircraft) {
        return;
    }

    if (!confirm(`Удалить борт ${aircraft.registration}?`)) {
        return;
    }

    try {
        await api('DELETE', `/api/admin/aircraft/${id}`);
        toast(`Борт ${aircraft.registration} удалён`, 'success');
        await loadAircraftTable();
        await loadFlightData();
    } catch (err) {
        toast(err.message, 'error');
    }
}

async function loadRoutesTable() {
    try {
        routesList = await api('GET', '/api/admin/routes');
        renderRoutesTable();
        fillRoutesSelect();
        updateExchangeRateState();
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

    tbody.innerHTML = routesList.map(route => `
        <tr>
            <td><strong>${escapeHtml(route.origin_iata)}</strong> ${escapeHtml(route.origin_city)}</td>
            <td><strong>${escapeHtml(route.destination_iata)}</strong> ${escapeHtml(route.destination_city)}</td>
            <td>${route.is_domestic ? 'Внутренний' : 'Международный'}</td>
            <td>${route.flight_duration_min ?? '—'}</td>
            <td>${route.distance_km ?? '—'}</td>
            <td class="actions">
                <button class="btn-icon" data-edit-route="${route.id}">Изм.</button>
                <button class="btn-icon danger" data-delete-route="${route.id}">Удал.</button>
            </td>
        </tr>
    `).join('');

    tbody.querySelectorAll('[data-edit-route]').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = parseInt(btn.dataset.editRoute, 10);
            const route = routesList.find(item => item.id === id);
            openRouteModal(route);
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
    $('rt-is_domestic').checked = Boolean(data?.is_domestic);
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
    if (e.target === $('route-modal')) {
        closeRouteModal();
    }
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
            toast('Маршрут обновлён', 'success');
        } else {
            await api('POST', '/api/admin/routes', payload);
            toast('Маршрут добавлен', 'success');
        }

        closeRouteModal();
        await loadRoutesTable();
        await loadFlightData();
    } catch (err) {
        toast(err.message, 'error');
    }
});

async function deleteRoute(id) {
    const route = routesList.find(item => item.id === id);

    if (!route) {
        return;
    }

    if (!confirm(`Удалить маршрут ${route.origin_iata} → ${route.destination_iata}?`)) {
        return;
    }

    try {
        await api('DELETE', `/api/admin/routes/${id}`);
        toast('Маршрут удалён', 'success');
        await loadRoutesTable();
        await loadFlightData();
    } catch (err) {
        toast(err.message, 'error');
    }
}

loadFlightData();