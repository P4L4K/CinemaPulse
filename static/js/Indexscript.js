document.addEventListener('DOMContentLoaded', () => {
    
    // 1. Scroll Animation Observer
    // This looks for any element with class 'scroll-animate'
    const observerOptions = {
        threshold: 0.2 // Trigger when 20% of the element is visible
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, observerOptions);

    const scrollElements = document.querySelectorAll('.scroll-animate');
    scrollElements.forEach(el => observer.observe(el));


    // 2. Navbar Hamburger Toggle (Mobile)
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');

    if (hamburger) {
        hamburger.addEventListener('click', () => {
            // Toggle display based on current state
            if (navLinks.style.display === 'flex') {
                navLinks.style.display = 'none';
            } else {
                navLinks.style.display = 'flex';
                navLinks.style.flexDirection = 'column';
                navLinks.style.position = 'absolute';
                navLinks.style.top = '70px';
                navLinks.style.right = '0';
                navLinks.style.width = '100%';
                navLinks.style.background = 'rgba(26, 26, 46, 0.98)';
                navLinks.style.padding = '2rem';
                navLinks.style.textAlign = 'center';
            }
        });
    }

    // 3. Smooth Scroll for Anchor Links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth'
                });
                // Close mobile menu if open
                if (window.innerWidth <= 768) {
                    navLinks.style.display = 'none';
                }
            }
        });
    });
});

//admin dashboard
/* === MODAL OPERATIONS === */
function openAddModal() {
    const form = document.getElementById("movieForm");
    form.action = "/admin/movie/add";

    document.getElementById("modalTitle").innerText = "Add New Movie";
    
    // Reset Form
    document.getElementById("movieName").value = "";
    document.getElementById("movieGenre").value = "";
    document.getElementById("movieLanguage").value = "";
    document.getElementById("movieImage").value = "";
    

    // Show input fields
    toggleInputVisibility(true);
    
    // Style confirm button
    const btn = document.querySelector(".save-btn");
    btn.innerText = "Save Movie";
    btn.style.backgroundColor = "#4ECDC4";
    btn.style.color = "#1A1A2E";

    document.getElementById("movieModal").style.display = "flex";
}

function openEditModal(name, genre, language, rating, image) {
    const form = document.getElementById("movieForm");
    form.action = "/admin/movie/update";

    document.getElementById("modalTitle").innerText = "Edit Movie Details";
    document.getElementById("oldMovieName").value = name;
    
    // Fill Form
    document.getElementById("movieName").value = name;
    document.getElementById("movieGenre").value = genre;
    document.getElementById("movieLanguage").value = language;
    document.getElementById("movieImage").value = image;

    toggleInputVisibility(true);

    const btn = document.querySelector(".save-btn");
    btn.innerText = "Update Changes";
    btn.style.backgroundColor = "#FFE66D";
    btn.style.color = "#1A1A2E";

    document.getElementById("movieModal").style.display = "flex";
}

function openDeleteModal(movieName) {
    const form = document.getElementById("movieForm");
    form.action = "/admin/movie/delete";

    document.getElementById("modalTitle").innerText = "Delete Movie?";
    document.getElementById("movieName").value = movieName;
    document.getElementById("oldMovieName").value = movieName;

    // Hide unnecessary inputs, show warning
    toggleInputVisibility(false);
    
    // Style confirm button
    const btn = document.querySelector(".save-btn");
    btn.innerText = "Confirm Deletion";
    btn.style.backgroundColor = "#FF6B6B";
    btn.style.color = "white";

    document.getElementById("movieModal").style.display = "flex";
}

function closeModal() {
    document.getElementById("movieModal").style.display = "none";
}

// Helper to show/hide fields based on action
function toggleInputVisibility(showAll) {
    const displayStyle = showAll ? "block" : "none";
    document.getElementById("movieGenre").closest('.form-group').style.display = displayStyle;
    document.getElementById("movieLanguage").closest('.form-group').style.display = displayStyle;
    document.getElementById("movieImage").closest('.form-group').style.display = displayStyle;
    
    // Toggle warning box
    document.getElementById("deleteWarning").style.display = showAll ? "none" : "flex";
    
    // Name input is read-only for delete, editable for others
    document.getElementById("movieName").readOnly = !showAll;
}

/* === SEARCH & FILTER === */
document.addEventListener("DOMContentLoaded", () => {
    const search = document.querySelector(".movie-search");
    const filter = document.querySelector(".movie-filter");
    const cards = document.querySelectorAll(".movie-card");

    function filterMovies() {
        const text = search.value.toLowerCase();
        const genre = filter.value.toLowerCase();

        cards.forEach(card => {
            const title = card.querySelector("h2").innerText.toLowerCase();
            const cardGenre = card.dataset.genre || ""; // Safe access

            const matchText = title.includes(text);
            const matchGenre = genre === "all" || cardGenre.includes(genre);

            card.style.display = (matchText && matchGenre) ? "flex" : "none";
        });
    }

    search.addEventListener("input", filterMovies);
    filter.addEventListener("change", filterMovies);
});

/* === CHART LOGIC (IMPROVED) === */
document.addEventListener("DOMContentLoaded", function () {
    const ctx = document.getElementById("genrePieChart");

    if (!ctx) return;

    // 1. Aggregation Logic: Calculate Average Rating per Genre
    const genreGroups = {}; // { Action: [4.5, 3.0], Drama: [5.0] }

    document.querySelectorAll(".movie-card").forEach(card => {
        // Get clean data
        const genreRaw = card.querySelector(".genre-tag").innerText;
        const genre = genreRaw.split("•")[0].trim(); 
        
        const ratingRaw = card.querySelector(".rating-badge").innerText;
        const rating = parseFloat(ratingRaw.replace("⭐", "").trim());

        if (!genreGroups[genre]) {
            genreGroups[genre] = [];
        }
        if(!isNaN(rating)) {
            genreGroups[genre].push(rating);
        }
    });

    // 2. Calculate Averages
    const labels = Object.keys(genreGroups);
    const dataPoints = labels.map(g => {
        const ratings = genreGroups[g];
        const sum = ratings.reduce((a, b) => a + b, 0);
        return (sum / ratings.length).toFixed(1); // Average
    });

    // 3. Render Chart
    new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [{
                data: dataPoints,
                backgroundColor: ['#FF6B6B', '#4ECDC4', '#FFE66D', '#6C63FF', '#FF9F43'],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { 
                        color: "#a0a0b0",
                        usePointStyle: true,
                        padding: 20
                    }
                }
            },
            cutout: '70%' // Thinner ring
        }
    });
});

/* === EVENT LISTENERS FOR DYNAMIC BUTTONS === */
document.addEventListener("DOMContentLoaded", () => {
    // We attach listeners to the container (Event Delegation) 
    // or direct elements since they are rendered server-side.
    
    // EDIT buttons
    document.querySelectorAll(".edit-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            openEditModal(
                btn.dataset.name,
                btn.dataset.genre,
                btn.dataset.language,
                btn.dataset.image
            );
        });
    });

    // DELETE buttons
    document.querySelectorAll(".delete-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            openDeleteModal(btn.dataset.name);
        });
    });
    
    // Close modal if clicking outside box
    window.onclick = function(event) {
        const modal = document.getElementById("movieModal");
        if (event.target == modal) {
            closeModal();
        }
    }
});

//user dashboard

function openFeedbackModal(movieName) {
    document.getElementById("movieNameInput").value = movieName;
    document.getElementById("feedbackModal").style.display = "flex";
}
function closeFeedbackModal() {
    document.getElementById("feedbackModal").style.display = "none";
}
function toggleFavorite(movieId, el) {
    fetch(`/movie/favorite/toggle/${movieId}`, {
        method: "POST",
        credentials: "same-origin"   
    })
    .then(res => res.json())
    .then(data => {
        console.log(data);  // Debug

        if (data.success) {
            const icon = el.querySelector("i");

            // Toggle heart icon
            if (data.is_favorite) {
                icon.classList.remove("far");
                icon.classList.add("fas");
            } else {
                icon.classList.remove("fas");
                icon.classList.add("far");
            }

            // Update favorites counter
            const favBox = document.querySelector(".stat-card .fa-heart").closest(".stat-card");
            const favCount = favBox.querySelector("p");
            favCount.innerText = data.total_favorites;
        } else {
            alert(data.message);
        }
    })
    .catch(err => console.error("Favorite toggle error:", err));
}

