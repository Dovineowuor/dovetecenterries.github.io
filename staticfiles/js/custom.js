$(function(){
    'use strict';

    // Initialize AOS with optimized settings
    AOS.init({
        duration: 800,
        easing: 'ease-in-out',
        once: true,
        mirror: false,
        offset: 50,
        delay: 100
    });

    // Immediately Invoked Function Expressions for better organization

    // Page loader - removed from markup; force-hide any leftovers (DOM + inline)
    (function() {
        ['.loader', '#overlayer'].forEach(function(sel) {
            document.querySelectorAll(sel).forEach(function(el) {
                el.style.setProperty('display', 'none', 'important');
                el.style.setProperty('visibility', 'hidden', 'important');
                el.style.setProperty('pointer-events', 'none', 'important');
                el.style.setProperty('opacity', '0', 'important');
                if (el.parentNode) el.parentNode.removeChild(el);
            });
        });
    })();

    // Site menu functionality
    const siteMenu = (function() {
        // Clone navigation for mobile
        $('.js-clone-nav').each(function() {
            $(this).clone().attr('class', 'site-nav-wrap').appendTo('.site-mobile-menu-body');
        });

        // Mobile menu setup with dynamic IDs
        setTimeout(function() {
            let counter = 0;
            $('.site-mobile-menu .has-children').each(function(){
                const $this = $(this);
                $this.prepend('<span class="arrow-collapse collapsed">');
                
                $this.find('.arrow-collapse').attr({
                    'data-toggle': 'collapse',
                    'data-target': '#collapseItem' + counter
                });

                $this.find('> ul').attr({
                    'class': 'collapse',
                    'id': 'collapseItem' + counter
                });
                counter++;
            });
        }, 1000);

        // Event handlers
        $('body').on('click', '.arrow-collapse', function(e) {
            e.preventDefault();
            const $this = $(this);
            $this.toggleClass('active', !$this.closest('li').find('.collapse').hasClass('show'));
        });

        // Responsive menu handling
        $(window).on('resize', function() {
            if ($(this).width() > 768) {
                $('body').removeClass('offcanvas-menu');
            }
        });

        // Menu toggle
        $('body').on('click', '.js-menu-toggle', function(e) {
            e.preventDefault();
            $('body').toggleClass('offcanvas-menu');
            $(this).toggleClass('active');
        });

        // Click outside menu handling
        $(document).on('mouseup', function(e) {
            const container = $(".site-mobile-menu");
            if (!container.is(e.target) && container.has(e.target).length === 0) {
                $('body').removeClass('offcanvas-menu');
                $('.js-menu-toggle').removeClass('active');
            }
        });
    })();

    // Carousel functionality
    const carouselManager = (function() {
        // Common carousel configuration
        const commonConfig = {
            loop: true,
            autoHeight: true,
            autoplay: true,
            nav: true,
            dots: true,
            navText: ['<span class="icon-keyboard_backspace"></span>','<span class="icon-keyboard_backspace"></span>'],
            smartSpeed: 700
        };

        // Initialize single item carousel
        if ($('.owl-single').length) {
            const owlSingle = $('.owl-single').owlCarousel($.extend({}, commonConfig, {
                items: 1,
                margin: 0,
                smartSpeed: 1000
            }));

            // Event delegation for navigation
            $(document).on('click', '.custom-owl-next', function(e) {
                e.preventDefault();
                owlSingle.trigger('next.owl.carousel');
            });
            $(document).on('click', '.custom-owl-prev', function(e) {
                e.preventDefault();
                owlSingle.trigger('prev.owl.carousel');
            });
        }

        // Initialize logo carousel
        if ($('.owl-logos').length) {
            $('.owl-logos').owlCarousel($.extend({}, commonConfig, {
                responsive: {
                    0: { items: 1 },
                    600: { items: 1 },
                    800: { items: 2 },
                    1000: { items: 3 },
                    1100: { items: 5 }
                }
            }));
        }

        // Initialize owl-3-slider
        if ($('.owl-3-slider').length) {
            const owl3 = $('.owl-3-slider').owlCarousel($.extend({}, commonConfig, {
                responsive: {
                    0: { items: 1 },
                    600: { items: 1 },
                    800: { items: 2 },
                    1000: { items: 2 },
                    1100: { items: 3 }
                }
            }));

            // Navigation event delegation
            $(document).on('click', '.owl-3-slider-next', function(e) {
                e.preventDefault();
                owl3.trigger('next.owl.carousel');
            });
            $(document).on('click', '.owl-3-slider-prev', function(e) {
                e.preventDefault();
                owl3.trigger('prev.owl.carousel');
            });
        }

        // Initialize owl-4-slider
        if ($('.owl-4-slider').length) {
            const owl4 = $('.owl-4-slider').owlCarousel($.extend({}, commonConfig, {
                responsive: {
                    0: { items: 1 },
                    600: { items: 2 },
                    800: { items: 2 },
                    1000: { items: 3 },
                    1100: { items: 4 }
                }
            }));

            // Navigation event delegation
            $(document).on('click', '.owl-4-slider-next', function(e) {
                e.preventDefault();
                owl4.trigger('next.owl.carousel');
            });
            $(document).on('click', '.owl-4-slider-prev', function(e) {
                e.preventDefault();
                owl4.trigger('prev.owl.carousel');
            });
        }
    })();

    // Counter animation
    const counterAnimation = (function() {
        $('.count-numbers').waypoint(function(direction) {
            if (direction === 'down' && !$(this.element).hasClass('ut-animated')) {
                const comma_separator = $.animateNumber.numberStepFactories.separator(',');
                $('.counter > span').each(function(){
                    const $this = $(this);
                    $this.animateNumber({
                        number: $this.data('number'),
                        numberStep: comma_separator
                    }, 10000);
                });
            }
        }, { offset: '95%' });
    })();

    // Portfolio masonry
    const portfolioHandler = (function() {
        if (!document.getElementById("portfolio-section")) return;

        const $grid = $(".grid").isotope({
            itemSelector: ".all",
            percentPosition: true,
            masonry: { columnWidth: ".all" }
        });

        $('.filters ul li').on('click', function(){
            $('.filters ul li').removeClass('active');
            $(this).addClass('active');
            $grid.isotope({ filter: $(this).attr('data-filter') });
        });

        $grid.imagesLoaded().progress(() => $grid.isotope('layout'));
    })();

    // Search functionality
    const searchHandler = (function() {
        $('.js-search-toggle').on('click', function() {
            $('.search-wrap').toggleClass('active');
            setTimeout(() => $('#s').focus(), 400);
        });

        $(document).on('mouseup', function(e) {
            const container = $(".search-wrap form");
            if (!container.is(e.target) && container.has(e.target).length === 0) {
                $('.search-wrap').removeClass('active');
            }
        });
    })();

    // Parallax effect
    const parallaxEffect = (function() {
        $(window).stellar({
            responsive: false,
            parallaxBackgrounds: true,
            parallaxElements: true,
            horizontalScrolling: false,
            hideDistantElements: false,
            scrollProperty: 'scroll'
        });
    })();

    // Pricing toggle
    const pricingToggle = (function() {
        $('.js-period-toggle').on('click', function(e) {
            e.preventDefault();
            const $this = $(this);
            const pricingItem = $('.pricing-item');
            $this.toggleClass('active');
            pricingItem.toggleClass('yearly', $this.hasClass('active'));
        });
    })();
});