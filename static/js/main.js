/* ============================================
   HelpDesk AI - Main JavaScript
   ============================================ */

document.addEventListener('DOMContentLoaded', function () {
    initFlashMessages();
    initAutoDismiss();
    initFileUpload();
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

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom(el) {
    if (el) el.scrollTop = el.scrollHeight;
}
