// JavaScript code to hide/show the table based on set contents
document.addEventListener('DOMContentLoaded', function () {
    var tableContainer = document.getElementById('tableContainer');
    if (!tableContainer.querySelector('table')) {
        tableContainer.style.display = 'none';  // Hide the table if set is empty
    }
});
