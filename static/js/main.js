$(document).ready(function() {
    updateCartCount();
    
    $('.add-to-cart-form').on('submit', function(e) {
        e.preventDefault();
        var form = $(this);
        var url = form.attr('action');
        var data = form.serialize();
        
        $.post(url, data, function(response) {
            showToast('Product added to cart!', 'success');
            updateCartCount();
        }).fail(function() {
            showToast('Error adding product to cart', 'danger');
        });
    });
    
    $('#search-input').on('keyup', function() {
        var query = $(this).val();
        if(query.length > 2) {
            $.get('/api/search', {q: query}, function(data) {
                displaySearchSuggestions(data);
            });
        }
    });
    
    if($('#price-range').length) {
        $('#price-range').on('change', function() {
            var min = $('#price-min').val();
            var max = $('#price-max').val();
            $('#price-min-display').text(min);
            $('#price-max-display').text(max);
        });
    }
    
    $('.quantity-btn').on('click', function() {
        var input = $(this).siblings('input');
        var currentVal = parseInt(input.val());
        var type = $(this).data('type');
        
        if(type === 'plus') {
            input.val(currentVal + 1);
        } else if(type === 'minus' && currentVal > 1) {
            input.val(currentVal - 1);
        }
    });
});

function updateCartCount() {
    $.get('/api/cart_count', function(data) {
        $('#cart-count').text(data.count);
        if(data.count > 0) {
            $('#cart-count').show();
        } else {
            $('#cart-count').hide();
        }
    });
}

function showToast(message, type) {
    var toastHtml = `
        <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    var toastContainer = $('.toast-notification');
    if(toastContainer.length === 0) {
        $('body').append('<div class="toast-notification"></div>');
        toastContainer = $('.toast-notification');
    }
    
    var toast = $(toastHtml);
    toastContainer.append(toast);
    var bsToast = new bootstrap.Toast(toast[0], {autohide: true, delay: 3000});
    bsToast.show();
    
    toast.on('hidden.bs.toast', function() {
        $(this).remove();
    });
}

function displaySearchSuggestions(products) {
    var suggestions = $('#search-suggestions');
    if(products.length > 0) {
        suggestions.empty().show();
        products.forEach(function(product) {
            suggestions.append(`
                <a href="/product/${product.id}" class="list-group-item list-group-item-action">
                    ${product.name} - ₦${product.price}
                </a>
            `);
        });
    } else {
        suggestions.hide();
    }
}

$(document).on('click', function(e) {
    if(!$(e.target).closest('#search-input').length) {
        $('#search-suggestions').hide();
    }
});

function confirmDelete(message) {
    return confirm(message || 'Are you sure you want to delete this item?');
}

function showLoading() {
    if($('.spinner-overlay').length === 0) {
        $('body').append('<div class="spinner-overlay"><div class="spinner-border text-light" role="status"></div></div>');
    }
    $('.spinner-overlay').addClass('active');
}

function hideLoading() {
    $('.spinner-overlay').removeClass('active');
}

function validateForm(formId) {
    var isValid = true;
    $(`#${formId} input[required], #${formId} textarea[required], #${formId} select[required]`).each(function() {
        if(!$(this).val()) {
            $(this).addClass('is-invalid');
            isValid = false;
        } else {
            $(this).removeClass('is-invalid');
        }
    });
    return isValid;
}

function isValidEmail(email) {
    var re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function isValidPhone(phone) {
    var re = /^0[789][01]\d{8}$/;
    return re.test(phone);
}

function addToWishlist(productId) {
    $.post(`/wishlist/add/${productId}`, function() {
        showToast('Added to wishlist!', 'success');
        $('#wishlist-icon-' + productId).removeClass('far').addClass('fas');
    }).fail(function() {
        showToast('Please login to add to wishlist', 'warning');
    });
}

function scrollToTop() {
    $('html, body').animate({scrollTop: 0}, 'smooth');
}

$(window).scroll(function() {
    if($(this).scrollTop() > 100) {
        $('#back-to-top').fadeIn();
    } else {
        $('#back-to-top').fadeOut();
    }
});

if($('#back-to-top').length === 0) {
    $('body').append('<button id="back-to-top" class="btn btn-primary rounded-circle" style="position: fixed; bottom: 20px; right: 20px; display: none;"><i class="fas fa-arrow-up"></i></button>');
    $('#back-to-top').on('click', scrollToTop);
}