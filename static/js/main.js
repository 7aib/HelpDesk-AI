/* ============================================
   HelpDesk AI - Main JavaScript
   ============================================ */

document.addEventListener('DOMContentLoaded', function () {
    initFlashMessages();
    initAutoDismiss();
    initFileUpload();
    initTheme();
    initSidebarCollapse();
    initChatSidebarToggle();
});

function initFlashMessages() {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });
}

function initAutoDismiss() {
    document.querySelectorAll('[data-bs-dismiss="alert"]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const alert = btn.closest('.alert');
            if (alert) {
                alert.style.opacity = '0';
                alert.style.transform = 'translateX(20px)';
                alert.style.transition = 'all 0.3s ease';
                setTimeout(function () { alert.remove(); }, 300);
            }
        });
    });
}

function initFileUpload() {
    document.querySelectorAll('.upload-area').forEach(function (area) {
        const input = area.querySelector('input[type="file"]');
        if (!input) return;

        area.addEventListener('click', function () { input.click(); });

        area.addEventListener('dragover', function (e) {
            e.preventDefault();
            area.classList.add('dragover');
        });

        area.addEventListener('dragleave', function () {
            area.classList.remove('dragover');
        });

        area.addEventListener('drop', function (e) {
            e.preventDefault();
            area.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                input.dispatchEvent(new Event('change'));
            }
        });

        input.addEventListener('change', function () {
            if (input.files.length) {
                const name = input.files[0].name;
                const label = area.querySelector('.upload-area-label');
                if (label) label.textContent = name;
            }
        });
    });
}

/* --- Theme Toggle --- */
function getTheme() {
    try { return localStorage.getItem('theme') || 'light'; } catch (e) { return 'light'; }
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.setAttribute('data-bs-theme', theme);
    const icon = document.getElementById('themeIcon');
    if (icon) icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
}

function initTheme() {
    applyTheme(getTheme());

    const toggles = [document.getElementById('themeToggle'), document.getElementById('themeFloat')];
    toggles.forEach(function (toggle) {
        if (!toggle) return;
        toggle.addEventListener('click', function () {
            const next = getTheme() === 'dark' ? 'light' : 'dark';
            try { localStorage.setItem('theme', next); } catch (e) {}
            applyTheme(next);
        });
    });
}

/* --- Sidebar Collapse --- */
function isMobile() {
    return window.matchMedia('(max-width: 991.98px)').matches;
}

function initSidebarCollapse() {
    const shell = document.getElementById('appShell');
    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('sidebarToggle');
    if (!shell || !sidebar || !toggle) return;

    if (!isMobile()) {
        try {
            const collapsed = localStorage.getItem('sidebar-collapsed') === '1';
            shell.classList.toggle('sidebar-collapsed', collapsed);
        } catch (e) {}
    }

    toggle.addEventListener('click', function () {
        if (isMobile()) {
            sidebar.classList.toggle('show');
            let backdrop = document.querySelector('.sidebar-backdrop');
            if (sidebar.classList.contains('show')) {
                if (!backdrop) {
                    backdrop = document.createElement('div');
                    backdrop.className = 'sidebar-backdrop';
                    document.body.appendChild(backdrop);
                    backdrop.addEventListener('click', function () {
                        sidebar.classList.remove('show');
                        backdrop.remove();
                    });
                }
            } else if (backdrop) {
                backdrop.remove();
            }
        } else {
            const collapsed = shell.classList.toggle('sidebar-collapsed');
            try { localStorage.setItem('sidebar-collapsed', collapsed ? '1' : '0'); } catch (e) {}
        }
    });
}

/* --- Chat Sidebar Toggle (mobile) --- */
function initChatSidebarToggle() {
    const toggle = document.getElementById('chatSidebarToggle');
    const sidebar = document.getElementById('chatSidebar');
    if (!toggle || !sidebar) return;

    toggle.addEventListener('click', function () {
        sidebar.classList.toggle('show');
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom(el) {
    if (el) el.scrollTop = el.scrollHeight;
}
