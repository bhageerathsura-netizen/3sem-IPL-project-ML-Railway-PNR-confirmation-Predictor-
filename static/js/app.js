/**
 * RailPredict AI — Intelligent Trip Planner, PNR Forecaster & Digital Booking Simulator
 * Refined, Calm UI with Smooth Transitions, Real-time Train Search, and Official IRCTC E-Tickets.
 */

let trajectoryChart = null;
let featureImportanceChart = null;
let corridorsData = {};
let currentSelectedTrainForBooking = null;

// Presets for quick evaluation
const PRESETS = {
    high: {
        corridor: "Delhi-Mumbai",
        train_category: "Rajdhani/VB",
        coach_class: "3A",
        quota: "GNWL",
        current_wl: 8,
        lead_time_days: 28,
        is_festive_season: 0,
        is_weekend: 0
    },
    medium: {
        corridor: "Delhi-Kolkata",
        train_category: "Superfast",
        coach_class: "3A",
        quota: "GNWL",
        current_wl: 38,
        lead_time_days: 12,
        is_festive_season: 0,
        is_weekend: 1
    },
    low: {
        corridor: "Delhi-Bangalore",
        train_category: "Superfast",
        coach_class: "SL",
        quota: "PQWL",
        current_wl: 65,
        lead_time_days: 4,
        is_festive_season: 1,
        is_weekend: 1
    }
};

document.addEventListener("DOMContentLoaded", () => {
    initCorridors();
    initTabNavigation();
    initEventListeners();
    initDatePickers();
    loadMetrics();
    startTatkalTimer();
    
    // Auto-search default corridor for trains
    performTrainSearch();
    // Run default PNR prediction on load
    runPrediction();
});

function initDatePickers() {
    const searchDateInput = document.getElementById("searchDate");
    if (searchDateInput) {
        const today = new Date();
        today.setDate(today.getDate() + 10);
        searchDateInput.value = today.toISOString().split("T")[0];
        searchDateInput.min = new Date().toISOString().split("T")[0];
    }
}

function initTabNavigation() {
    const navTabs = [
        { btn: "tabBtnSearch", content: "tabContentSearch" },
        { btn: "tabBtnForecast", content: "tabContentForecast" },
        { btn: "tabBtnMyTickets", content: "tabContentMyTickets" },
        { btn: "tabBtnTatkal", content: "tabContentTatkal" }
    ];

    navTabs.forEach(t => {
        const btn = document.getElementById(t.btn);
        if (btn) {
            btn.addEventListener("click", () => {
                navTabs.forEach(item => {
                    const b = document.getElementById(item.btn);
                    const c = document.getElementById(item.content);
                    if (item.btn === t.btn) {
                        b.classList.add("active");
                        c.classList.remove("hidden");
                    } else {
                        b.classList.remove("active");
                        c.classList.add("hidden");
                    }
                });

                if (t.btn === "tabBtnMyTickets") {
                    loadBookedTickets();
                }
            });
        }
    });

    // Quick shortcut button inside tickets tab
    const btnNewSearch = document.getElementById("btnNewSearchFromTickets");
    if (btnNewSearch) {
        btnNewSearch.addEventListener("click", () => {
            document.getElementById("tabBtnSearch").click();
        });
    }
}

async function initCorridors() {
    try {
        const response = await fetch("/api/corridors");
        const data = await response.json();
        if (data.status === "success") {
            corridorsData = data.corridors;

            // Populate both corridor selectors
            const corridorSelect = document.getElementById("corridor");
            const searchCorridorSelect = document.getElementById("searchCorridor");
            corridorSelect.innerHTML = "";
            searchCorridorSelect.innerHTML = "";

            Object.keys(corridorsData).forEach(corr => {
                const opt1 = document.createElement("option");
                opt1.value = corr;
                opt1.textContent = `${corr} (${corridorsData[corr].distance_km} km)`;
                corridorSelect.appendChild(opt1);

                const opt2 = document.createElement("option");
                opt2.value = corr;
                opt2.textContent = `${corridorsData[corr].origin_name} ➔ ${corridorsData[corr].dest_name} (${corr})`;
                searchCorridorSelect.appendChild(opt2);
            });

            updateTrainOptions();
        }
    } catch (err) {
        console.error("Failed to load corridors:", err);
    }
}

function updateTrainOptions() {
    const selectedCorridor = document.getElementById("corridor").value;
    const trainSelect = document.getElementById("popularTrain");
    trainSelect.innerHTML = "<option value=''>Custom / Select Train</option>";

    if (corridorsData[selectedCorridor]) {
        const trains = corridorsData[selectedCorridor].popular_trains;
        trains.forEach(t => {
            const opt = document.createElement("option");
            opt.value = JSON.stringify(t);
            opt.textContent = `${t.number} - ${t.name} (${t.category})`;
            trainSelect.appendChild(opt);
        });
    }
}

function initEventListeners() {
    // Corridor change in Forecast view
    document.getElementById("corridor").addEventListener("change", () => {
        updateTrainOptions();
    });

    document.getElementById("popularTrain").addEventListener("change", (e) => {
        if (!e.target.value) return;
        const train = JSON.parse(e.target.value);
        document.getElementById("trainCategory").value = train.category;
        if (train.classes && train.classes.length > 0) {
            const classSelect = document.getElementById("coachClass");
            if (!train.classes.includes(classSelect.value)) {
                classSelect.value = train.classes[0];
            }
        }
    });

    // PNR Prediction Form Submit
    document.getElementById("predictionForm").addEventListener("submit", (e) => {
        e.preventDefault();
        runPrediction();
    });

    // Train Search Form Submit
    document.getElementById("trainSearchForm").addEventListener("submit", (e) => {
        e.preventDefault();
        performTrainSearch();
    });

    // Interactive slider sync
    const leadSlider = document.getElementById("leadTimeSlider");
    const leadInput = document.getElementById("leadTimeDays");
    leadSlider.addEventListener("input", (e) => { leadInput.value = e.target.value; });
    leadInput.addEventListener("input", (e) => { leadSlider.value = e.target.value; });

    const wlSlider = document.getElementById("wlSlider");
    const wlInput = document.getElementById("currentWl");
    wlSlider.addEventListener("input", (e) => { wlInput.value = e.target.value; });
    wlInput.addEventListener("input", (e) => { wlSlider.value = e.target.value; });

    // Presets
    document.querySelectorAll("[data-preset]").forEach(btn => {
        btn.addEventListener("click", () => {
            const presetKey = btn.getAttribute("data-preset");
            applyPreset(PRESETS[presetKey]);
        });
    });

    // What-If Matrix simulation button
    document.getElementById("btnRunSimulation").addEventListener("click", () => {
        runSimulationMatrix();
    });

    // Modal Close Listeners
    document.getElementById("btnCloseModal").addEventListener("click", () => {
        document.getElementById("bookingModal").classList.remove("open");
    });

    document.getElementById("btnCloseTicketModal").addEventListener("click", () => {
        document.getElementById("ticketModal").classList.remove("open");
    });

    document.getElementById("btnDoneTicket").addEventListener("click", () => {
        document.getElementById("ticketModal").classList.remove("open");
        document.getElementById("tabBtnMyTickets").click();
    });

    document.getElementById("btnPrintTicket").addEventListener("click", () => {
        window.print();
    });

    // Passenger Booking Submit
    document.getElementById("passengerBookingForm").addEventListener("submit", (e) => {
        e.preventDefault();
        submitTicketBooking();
    });
}

function applyPreset(p) {
    document.getElementById("tabBtnForecast").click();
    document.getElementById("corridor").value = p.corridor;
    updateTrainOptions();
    document.getElementById("trainCategory").value = p.train_category;
    document.getElementById("coachClass").value = p.coach_class;
    document.getElementById("quota").value = p.quota;
    document.getElementById("currentWl").value = p.current_wl;
    document.getElementById("wlSlider").value = p.current_wl;
    document.getElementById("leadTimeDays").value = p.lead_time_days;
    document.getElementById("leadTimeSlider").value = p.lead_time_days;
    document.getElementById("isFestive").checked = p.is_festive_season === 1;
    document.getElementById("isWeekend").checked = p.is_weekend === 1;
    runPrediction();
}

// ============================================================================
// TRIP PLANNER & TRAIN SEARCH ENGINE
// ============================================================================

async function performTrainSearch() {
    const corridor = document.getElementById("searchCorridor").value || "Delhi-Mumbai";
    const travelDate = document.getElementById("searchDate").value || "";
    const preferredClass = document.getElementById("searchClass").value || "3A";
    const quota = document.getElementById("searchQuota").value || "GNWL";

    const btn = document.getElementById("btnSearchTrains");
    btn.disabled = true;
    btn.innerHTML = `<span class="inline-block animate-spin mr-2">⚙</span> Finding Services...`;

    try {
        const url = `/api/search_trains?corridor=${encodeURIComponent(corridor)}&date=${encodeURIComponent(travelDate)}&class=${encodeURIComponent(preferredClass)}&quota=${encodeURIComponent(quota)}`;
        const response = await fetch(url);
        const res = await response.json();

        if (res.status === "success") {
            renderTrainSearchResults(res);
        }
    } catch (err) {
        console.error("Search failed:", err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg><span>Find Available Trains</span>`;
    }
}

function renderTrainSearchResults(data) {
    document.getElementById("searchResultsHeader").textContent = `${data.origin} ➔ ${data.destination}`;
    document.getElementById("searchResultsSub").textContent = `Departure on ${data.travel_date} (${data.days_left} days left). Real-time confirmation intelligence.`;
    document.getElementById("trainsFoundCount").textContent = `${data.trains.length} Direct Express Services`;

    // 1. Render Smart Route Box
    const smart = data.split_journey;
    const smartBox = document.getElementById("smartRouteBox");
    if (smart) {
        smartBox.classList.remove("hidden");
        document.getElementById("smartRouteTitle").textContent = smart.title;
        document.getElementById("smartRouteDesc").textContent = `${smart.advantage}. Connects via ${smart.hub} with comfortable layover.`;
        
        const pills = document.getElementById("smartRoutePills");
        pills.innerHTML = `
            <span class="px-2.5 py-1 rounded bg-white/10 border border-white/20 font-medium">Leg 1: ${smart.leg1.train} (${smart.leg1.status})</span>
            <span class="px-2.5 py-1 rounded bg-white/10 border border-white/20 font-medium">Leg 2: ${smart.leg2.train} (${smart.leg2.status})</span>
            <span class="px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-400/40 font-bold">Total Time: ${smart.total_duration}</span>
        `;

        document.getElementById("btnBookSmartRoute").onclick = () => {
            openBookingModal({
                train_number: smart.leg2.train.split(" ")[0],
                train_name: `${smart.title} (${smart.hub})`,
                coach_class: "3A",
                fare: 2240,
                availability: "AVL (Confirmed Connection)",
                corridor: data.corridor,
                travel_date: data.travel_date
            });
        };
    } else {
        smartBox.classList.add("hidden");
    }

    // 2. Render Direct Train Cards
    const listContainer = document.getElementById("trainListContainer");
    listContainer.innerHTML = "";

    data.trains.forEach(t => {
        const card = document.createElement("div");
        card.className = "train-card space-y-4";

        let classesHtml = "";
        t.class_options.forEach(opt => {
            let statusBadge = "";
            let aiBadge = "";

            if (opt.availability.includes("AVL")) {
                statusBadge = `<span class="badge-available">${opt.availability}</span>`;
                aiBadge = `<span class="text-[10px] text-emerald-700 font-semibold">Instant Allotment</span>`;
            } else if (opt.availability.includes("RAC")) {
                statusBadge = `<span class="badge-rac">${opt.availability}</span>`;
                aiBadge = `<span class="badge-ai-prob">⚡ ${opt.ai_probability}% RAC Allotment</span>`;
            } else {
                statusBadge = `<span class="badge-waitlist">${opt.availability}</span>`;
                if (opt.ai_probability >= 75) {
                    aiBadge = `<span class="badge-ai-prob text-emerald-700 bg-emerald-50 border-emerald-200">⚡ ${opt.ai_probability}% Confirm Chance (Safe)</span>`;
                } else if (opt.ai_probability >= 40) {
                    aiBadge = `<span class="badge-ai-prob text-amber-700 bg-amber-50 border-amber-200">⚡ ${opt.ai_probability}% RAC Likely</span>`;
                } else {
                    aiBadge = `<span class="badge-ai-prob text-rose-700 bg-rose-50 border-rose-200">⚠️ ${opt.ai_probability}% High Risk Drop</span>`;
                }
            }

            classesHtml += `
                <div class="class-pill flex flex-col justify-between" data-book-train='${JSON.stringify({
                    train_number: t.number,
                    train_name: t.name,
                    coach_class: opt.coach_class,
                    fare: opt.fare,
                    availability: opt.availability,
                    corridor: data.corridor,
                    travel_date: data.travel_date
                })}'>
                    <div class="flex items-center justify-between mb-1">
                        <span class="font-extrabold text-slate-900 mono text-sm">${opt.coach_class}</span>
                        <span class="font-black text-slate-800 text-sm mono">₹${opt.fare}</span>
                    </div>
                    <div class="mb-2">
                        ${statusBadge}
                    </div>
                    <div class="mb-2">
                        ${aiBadge}
                    </div>
                    <button type="button" class="btn-primary text-xs py-1.5 px-3 w-full justify-center mt-1">
                        Book Berth
                    </button>
                </div>
            `;
        });

        card.innerHTML = `
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
                <div>
                    <div class="flex items-center space-x-2">
                        <span class="font-black text-slate-900 text-base mono">${t.number}</span>
                        <span class="font-bold text-slate-800 text-base">${t.name}</span>
                        <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">${t.category}</span>
                    </div>
                    <div class="text-xs text-slate-500 mt-0.5">Runs: ${t.runs_on}</div>
                </div>
                <div class="flex items-center space-x-4 text-xs font-semibold">
                    <div class="text-left">
                        <span class="text-base font-extrabold text-slate-900 block mono">${t.dep_time}</span>
                        <span class="text-slate-500">${t.origin_code}</span>
                    </div>
                    <div class="text-center px-2 py-0.5 rounded bg-slate-100 text-slate-600 mono text-[11px]">
                        ${t.duration}
                    </div>
                    <div class="text-right">
                        <span class="text-base font-extrabold text-slate-900 block mono">${t.arr_time}</span>
                        <span class="text-slate-500">${t.dest_code}</span>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 pt-1">
                ${classesHtml}
            </div>
        `;

        // Bind booking clicks
        card.querySelectorAll(".class-pill button").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const parent = btn.closest(".class-pill");
                const bookingData = JSON.parse(parent.getAttribute("data-book-train"));
                openBookingModal(bookingData);
            });
        });

        listContainer.appendChild(card);
    });
}

function openBookingModal(data) {
    currentSelectedTrainForBooking = data;
    document.getElementById("modalTrainInfo").textContent = `${data.train_number} ${data.train_name} • Class ${data.coach_class} (${data.availability})`;
    document.getElementById("modalBaseFare").textContent = `₹${data.fare.toFixed(2)}`;
    
    const convenience = 17.70;
    const grand = data.fare + convenience;
    document.getElementById("modalGrandTotal").textContent = `₹${grand.toFixed(2)}`;

    document.getElementById("bookingModal").classList.add("open");
}

async function submitTicketBooking() {
    if (!currentSelectedTrainForBooking) return;

    const passengerName = document.getElementById("p1Name").value.trim() || "Passenger";
    const passengerAge = parseInt(document.getElementById("p1Age").value) || 28;
    const passengerGender = document.getElementById("p1Gender").value;
    const berthPref = document.getElementById("p1BerthPref").value;
    const btn = document.getElementById("btnConfirmReservation");

    btn.disabled = true;
    btn.innerHTML = `<span class="inline-block animate-spin mr-2">⚙</span> Confirming Berth Reservation...`;

    try {
        const payload = {
            train_number: currentSelectedTrainForBooking.train_number,
            train_name: currentSelectedTrainForBooking.train_name,
            coach_class: currentSelectedTrainForBooking.coach_class,
            quota: document.getElementById("searchQuota").value || "GNWL",
            travel_date: currentSelectedTrainForBooking.travel_date,
            corridor: currentSelectedTrainForBooking.corridor,
            total_fare: currentSelectedTrainForBooking.fare,
            availability: currentSelectedTrainForBooking.availability,
            passengers: [
                { name: passengerName, age: passengerAge, gender: passengerGender, berth_pref: berthPref }
            ]
        };

        const response = await fetch("/api/book_ticket", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const res = await response.json();

        if (res.status === "success") {
            document.getElementById("bookingModal").classList.remove("open");
            showOfficialTicket(res.ticket);
            loadBookedTickets();
        } else {
            alert("Booking failed: " + res.message);
        }
    } catch (err) {
        console.error("Booking failed:", err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>Confirm & Generate Digital E-Ticket</span><svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`;
    }
}

function showOfficialTicket(ticket) {
    document.getElementById("ticketBookingTime").textContent = `Reserved: ${ticket.booking_timestamp}`;
    document.getElementById("ticketPnr").textContent = ticket.pnr;
    document.getElementById("ticketTrain").textContent = `${ticket.train_number} - ${ticket.train_name}`;
    document.getElementById("ticketClassQuota").textContent = `${ticket.coach_class} • ${ticket.quota}`;
    document.getElementById("ticketDate").textContent = ticket.travel_date;
    document.getElementById("ticketFare").textContent = `₹${ticket.grand_total.toFixed(2)}`;
    document.getElementById("ticketRoute").textContent = `${ticket.from_station} ➔ ${ticket.to_station}`;

    const tbody = document.getElementById("ticketPassengerRows");
    tbody.innerHTML = "";

    ticket.passengers.forEach((p, idx) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="p-2 font-bold mono text-slate-700">${idx + 1}</td>
            <td class="p-2 font-bold text-slate-900">${p.name}</td>
            <td class="p-2 text-slate-600">${p.age} / ${p.gender}</td>
            <td class="p-2 font-bold text-emerald-700">${p.booking_status}</td>
            <td class="p-2 font-extrabold mono text-blue-900">${p.current_status}</td>
        `;
        tbody.appendChild(tr);
    });

    document.getElementById("ticketModal").classList.add("open");
}

async function loadBookedTickets() {
    try {
        const response = await fetch("/api/my_tickets");
        const res = await response.json();
        if (res.status === "success") {
            const list = document.getElementById("bookedTicketsList");
            const badge = document.getElementById("myTicketsCountBadge");
            badge.textContent = res.tickets.length;

            if (res.tickets.length === 0) {
                list.innerHTML = `
                    <div class="text-center py-12 text-slate-400">
                        <svg class="w-12 h-12 mx-auto text-slate-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z"></path></svg>
                        <p class="text-sm font-semibold text-slate-600">No tickets reserved yet in this session</p>
                        <p class="text-xs text-slate-400 mt-0.5">Search any train and click "Book Berth" to generate an official digital ticket.</p>
                    </div>
                `;
                return;
            }

            list.innerHTML = "";
            res.tickets.forEach(ticket => {
                const card = document.createElement("div");
                card.className = "p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-400 transition flex flex-col sm:flex-row sm:items-center justify-between gap-4";
                
                card.innerHTML = `
                    <div class="space-y-1">
                        <div class="flex items-center space-x-2">
                            <span class="text-xs font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-800 mono">PNR: ${ticket.pnr}</span>
                            <span class="text-xs font-bold text-slate-800">${ticket.train_number} ${ticket.train_name}</span>
                            <span class="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">CONFIRMED</span>
                        </div>
                        <div class="text-xs text-slate-600">
                            ${ticket.from_station} ➔ ${ticket.to_station} • Travel Date: <span class="font-semibold text-slate-900">${ticket.travel_date}</span>
                        </div>
                        <div class="text-xs text-slate-500">
                            Passenger: <span class="font-bold text-slate-800">${ticket.passengers[0].name}</span> (${ticket.passengers[0].current_status})
                        </div>
                    </div>
                    <div class="flex items-center space-x-3">
                        <span class="font-black mono text-base text-slate-900">₹${ticket.grand_total.toFixed(2)}</span>
                        <button class="btn-outline text-xs py-1.5 px-3 btn-view-ticket">View E-Ticket</button>
                    </div>
                `;

                card.querySelector(".btn-view-ticket").addEventListener("click", () => {
                    showOfficialTicket(ticket);
                });

                list.appendChild(card);
            });
        }
    } catch (err) {
        console.error("Failed to load tickets:", err);
    }
}

// ============================================================================
// PNR FORECAST & SPEEDOMETER ENGINE
// ============================================================================

function getFormPayload() {
    return {
        corridor: document.getElementById("corridor").value,
        train_category: document.getElementById("trainCategory").value,
        coach_class: document.getElementById("coachClass").value,
        quota: document.getElementById("quota").value,
        current_wl: parseInt(document.getElementById("currentWl").value) || 1,
        lead_time_days: parseInt(document.getElementById("leadTimeDays").value) || 1,
        is_festive_season: document.getElementById("isFestive").checked ? 1 : 0,
        is_weekend: document.getElementById("isWeekend").checked ? 1 : 0
    };
}

async function runPrediction() {
    const payload = getFormPayload();
    const btnSubmit = document.getElementById("btnPredict");
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = `<span class="inline-block animate-spin mr-2">⚙</span> Computing Classifier Inference...`;

    try {
        const response = await fetch("/api/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const res = await response.json();

        if (res.status === "success") {
            renderPredictionResults(res.data);
        }
    } catch (err) {
        console.error("Prediction failed:", err);
    } finally {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = `<span>Analyze Berth Confirmation</span><svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>`;
    }
}

function renderPredictionResults(data) {
    const prob = data.probability_pct;
    const tier = data.risk_tier;

    // 1. Update Gauge Circle
    const circle = document.getElementById("gaugeCircle");
    const radius = 85;
    const circumference = 2 * Math.PI * radius;
    circle.style.strokeDasharray = `${circumference} ${circumference}`;
    const offset = circumference - (prob / 100) * circumference;
    circle.style.strokeDashoffset = offset;

    let strokeColor = "#059669"; // Emerald
    let badgeClass = "badge-available";
    if (tier === "MEDIUM") {
        strokeColor = "#d97706"; // Amber
        badgeClass = "badge-rac";
    } else if (tier === "LOW") {
        strokeColor = "#dc2626"; // Red
        badgeClass = "badge-waitlist";
    }

    circle.style.stroke = strokeColor;
    document.getElementById("gaugePercentText").style.color = strokeColor;
    animateValue("gaugePercentText", 0, prob, 800);

    const badgeEl = document.getElementById("riskTierBadge");
    badgeEl.className = badgeClass;
    badgeEl.textContent = data.tier_label;

    document.getElementById("recommendationTitle").textContent = data.recommendation;
    document.getElementById("actionSummary").textContent = data.action_summary;

    const adviceList = document.getElementById("advicePointsList");
    adviceList.innerHTML = "";
    data.advice_points.forEach(pt => {
        const li = document.createElement("li");
        li.className = "flex items-start text-xs text-slate-700";
        li.innerHTML = `
            <svg class="w-3.5 h-3.5 mr-2 text-blue-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <span>${pt}</span>
        `;
        adviceList.appendChild(li);
    });

    renderTrajectoryChart(data.trajectory);
    renderQuotaComparison(data.quota_comparison);
    renderClassAlternatives(data.class_alternatives);
}

function animateValue(id, start, end, duration) {
    const obj = document.getElementById(id);
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const current = (progress * (end - start)) + start;
        obj.textContent = current.toFixed(1) + "%";
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

function renderTrajectoryChart(points) {
    const ctx = document.getElementById("trajectoryChartCanvas").getContext("2d");
    const sortedPoints = [...points].sort((a, b) => a.days_remaining - b.days_remaining);
    const labels = sortedPoints.map(p => `T - ${p.days_remaining}d`);
    const dataValues = sortedPoints.map(p => p.probability_pct);
    const wlValues = sortedPoints.map(p => p.projected_wl);

    if (trajectoryChart) trajectoryChart.destroy();

    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, "rgba(15, 35, 71, 0.20)");
    gradient.addColorStop(1, "rgba(15, 35, 71, 0.0)");

    trajectoryChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Confirmation Probability (%)",
                    data: dataValues,
                    borderColor: "#0f2347",
                    backgroundColor: gradient,
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.35,
                    pointBackgroundColor: "#ea580c",
                    pointBorderColor: "#ffffff",
                    pointBorderWidth: 2,
                    pointRadius: 3.5,
                    yAxisID: "y"
                },
                {
                    label: "Remaining Queue (WL)",
                    data: wlValues,
                    borderColor: "#94a3b8",
                    borderWidth: 1.8,
                    borderDash: [4, 4],
                    fill: false,
                    tension: 0.2,
                    pointRadius: 2.5,
                    yAxisID: "y1"
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: {
                    labels: { color: "#475569", font: { family: "Plus Jakarta Sans", size: 11 } }
                }
            },
            scales: {
                x: {
                    grid: { color: "rgba(0, 0, 0, 0.04)" },
                    ticks: { color: "#64748b", font: { size: 10 } }
                },
                y: {
                    type: "linear", display: true, position: "left",
                    min: 0, max: 100,
                    grid: { color: "rgba(0, 0, 0, 0.05)" },
                    ticks: { color: "#0f2347", font: { size: 10, weight: "bold" }, callback: v => v + "%" }
                },
                y1: {
                    type: "linear", display: true, position: "right",
                    grid: { drawOnChartArea: false },
                    ticks: { color: "#94a3b8", font: { size: 10 } }
                }
            }
        }
    });
}

function renderQuotaComparison(quotaList) {
    const container = document.getElementById("quotaComparisonContainer");
    container.innerHTML = "";

    quotaList.forEach(q => {
        let barColor = "bg-emerald-500";
        let textColor = "text-emerald-700";
        if (q.tier === "MEDIUM") {
            barColor = "bg-amber-500";
            textColor = "text-amber-700";
        } else if (q.tier === "LOW") {
            barColor = "bg-rose-500";
            textColor = "text-rose-700";
        }

        const div = document.createElement("div");
        div.className = "p-2.5 rounded-lg bg-slate-50 border border-slate-200";
        div.innerHTML = `
            <div class="flex justify-between items-center mb-1.5 text-xs">
                <span class="font-bold mono text-slate-800">${q.quota}</span>
                <span class="font-black ${textColor}">${q.probability_pct}%</span>
            </div>
            <div class="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                <div class="${barColor} h-2 rounded-full transition-all duration-700" style="width: ${q.probability_pct}%"></div>
            </div>
        `;
        container.appendChild(div);
    });
}

function renderClassAlternatives(alternatives) {
    const container = document.getElementById("classAlternativesContainer");
    container.innerHTML = "";

    if (!alternatives || alternatives.length === 0) {
        container.innerHTML = "<p class='text-xs text-slate-400'>No alternate classes available.</p>";
        return;
    }

    alternatives.slice(0, 4).forEach(alt => {
        let badgeCls = "badge-available";
        if (alt.tier === "MEDIUM") badgeCls = "badge-rac";
        if (alt.tier === "LOW") badgeCls = "badge-waitlist";

        const card = document.createElement("div");
        card.className = "p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex justify-between items-center text-xs";
        card.innerHTML = `
            <div>
                <div class="flex items-center space-x-1.5">
                    <span class="font-bold text-slate-900 mono">${alt.coach_class}</span>
                    <span class="${badgeCls}">${alt.probability_pct}%</span>
                </div>
                <div class="text-[10px] text-slate-500 mt-0.5">Est. WL: ${alt.simulated_wl}</div>
            </div>
            <button class="btn-outline text-[11px] py-1 px-2.5">Switch</button>
        `;

        card.querySelector("button").addEventListener("click", () => {
            document.getElementById("coachClass").value = alt.coach_class;
            document.getElementById("currentWl").value = alt.simulated_wl;
            document.getElementById("wlSlider").value = alt.simulated_wl;
            runPrediction();
        });

        container.appendChild(card);
    });
}

// ============================================================================
// WHAT-IF MATRIX & TATKAL ENGINE
// ============================================================================

async function runSimulationMatrix() {
    const payload = getFormPayload();
    const container = document.getElementById("simulationMatrixContainer");
    container.innerHTML = "<div class='text-center py-6 text-slate-400 animate-pulse text-xs'>Computing multi-dimensional scenario matrix...</div>";

    try {
        const response = await fetch("/api/simulate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const res = await response.json();

        if (res.status === "success") {
            const headers = res.days_headers;
            const matrix = res.matrix;

            let html = `
                <div class="overflow-x-auto">
                    <table class="w-full text-xs text-center border-collapse">
                        <thead>
                            <tr class="border-b border-slate-200 text-slate-500">
                                <th class="p-2.5 text-left font-semibold">Queue (WL) \\ Days Left</th>
                                ${headers.map(d => `<th class="p-2.5 font-semibold">${d} Days</th>`).join("")}
                            </tr>
                        </thead>
                        <tbody>
            `;

            matrix.forEach(row => {
                html += `
                    <tr class="border-b border-slate-100">
                        <td class="p-2 text-left font-bold mono text-slate-800">WL ${row.waitlist}</td>
                        ${row.scores.map(s => {
                            let cellBg = "#ecfdf5";
                            let cellText = "#059669";
                            if (s.tier === "MEDIUM") {
                                cellBg = "#fffbeb";
                                cellText = "#d97706";
                            } else if (s.tier === "LOW") {
                                cellBg = "#fef2f2";
                                cellText = "#dc2626";
                            }
                            return `
                                <td class="p-1">
                                    <div class="py-1 px-1 rounded mono font-semibold" style="background: ${cellBg}; color: ${cellText};">
                                        ${s.probability_pct}%
                                    </div>
                                </td>
                            `;
                        }).join("")}
                    </tr>
                `;
            });

            html += `</tbody></table></div>`;
            container.innerHTML = html;
        }
    } catch (err) {
        container.innerHTML = "<div class='text-rose-500 py-4 text-xs'>Failed to calculate matrix.</div>";
    }
}

function startTatkalTimer() {
    function updateClock() {
        const now = new Date();
        const target = new Date();
        target.setHours(10, 0, 0, 0);
        if (now > target) {
            target.setDate(target.getDate() + 1);
        }

        const diffSecs = Math.floor((target - now) / 1000);
        const hrs = String(Math.floor(diffSecs / 3600)).padStart(2, "0");
        const mins = String(Math.floor((diffSecs % 3600) / 60)).padStart(2, "0");
        const secs = String(diffSecs % 60).padStart(2, "0");

        const clockEl = document.getElementById("tatkalClockAC");
        if (clockEl) {
            clockEl.textContent = `${hrs}:${mins}:${secs}`;
        }
    }

    updateClock();
    setInterval(updateClock, 1000);
}

async function loadMetrics() {
    try {
        const response = await fetch("/api/metrics");
        const res = await response.json();
        if (res.status === "success") {
            const m = res.metrics;
            document.getElementById("metricAccuracy").textContent = (m.random_forest.accuracy * 100).toFixed(1) + "%";
            document.getElementById("metricAUC").textContent = m.random_forest.roc_auc.toFixed(4);
            document.getElementById("metricF1").textContent = m.random_forest.f1_score.toFixed(4);
            document.getElementById("metricDatasetSize").textContent = m.dataset_size.toLocaleString();

            renderFeatureImportanceChart(m.top_features);
        }
    } catch (err) {
        console.error("Failed to load metrics:", err);
    }
}

function renderFeatureImportanceChart(features) {
    const canvas = document.getElementById("featureImportanceChartCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const labels = features.map(f => f.feature);
    const values = features.map(f => (f.importance * 100).toFixed(1));

    if (featureImportanceChart) featureImportanceChart.destroy();

    featureImportanceChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Feature Importance (%)",
                data: values,
                backgroundColor: "rgba(15, 35, 71, 0.8)",
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: {
                    grid: { color: "rgba(0,0,0,0.05)" },
                    ticks: { color: "#64748b", font: { size: 10 } }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: "#1e293b", font: { family: "JetBrains Mono", size: 10 } }
                }
            }
        }
    });
}
