load_libraries(['_', 'jQuery', 'URI'], function(_, $, URI) {
    "use strict";

    /*
        Queries the current url with the parameter '&select-[field]=[value]'
        using ajax and goes through the result replacing the
        list-select-fragments on the current page with the ones found in
        the result of the ajax request. Each fragments needs its own id
        for this process to work:

        e.g.

        with this fragment...
        <div class="filter-fragment" id="filter-fragment-1" />

        ...this call...
        $.ListFilter().filter('country', 'CH')

        ..will request...
        http://my-url.com/index?x=1&select-country=CH

        ...and replace the mentioned fragment.
    */
    $.ListFilter = function(options) {

        var self = {};

        self.options = $.extend({
            'fragments': '.filter-fragment',
            'prefix': 'filter-'
        }, options);

        /*
            gets the current url, removing all traces of
            list selector's own query parameters
        */
        self.build_url = function(fieldmap) {
            var uri = URI(window.location.href);

            // remove the prefixed query arguments
            var params = uri.query(true);
            params = _.omit(params,
                _.filter(_.keys(params), function(key) {
                    return key.indexOf(self.options.prefix) != -1;
                })
            );

            // optionally add the given arguments
            if (! _.isUndefined(fieldmap)) {
                _.each(fieldmap, function(value, key) {

                    // add the prefix if not defined
                    if (key.indexOf(self.options.prefix) == -1) {
                        key = self.options.prefix + key;
                    }

                    params[key] = value;
                });
            }

            // reset the batching
            if (_.has(params, 'b_start:int')) {
                delete params['b_start:int'];
            }

            return uri.query(params).toString();
        };

        /*
            loads the given url and replaces the local
            fragments with the loaded fragments
        */
        self.load = function(url) {
            var carrier = $('<div>');
            var selector = url + ' ' + self.options.fragments;

            carrier.load(selector, function(data) {

                var map_fragments = function(fragments) {
                    return _.object(
                        _.map(fragments, function(fragment) {
                            return [fragment.id, fragment];
                        })
                    );
                };
                var selector = self.options.fragments;

                var local_fragments = map_fragments($(self.options.fragments));
                var loaded_fragments = map_fragments($(carrier).find(selector));

                _.each(loaded_fragments, function(fragment, id) {
                    if (_.has(local_fragments, id)) {
                        $(local_fragments[id]).replaceWith($(fragment));
                    }
                });

                // update the url if the browser supports it
                if (window.history.replaceState) {
                    var readable = new URI(url).readable();
                    window.history.replaceState({}, document.title, readable);
                }

                $(document).trigger('filter-fragments-loaded');
            });
        };

        /*
            filters the table with the given field/value. if either of those
            are undefined, the possibly filtered table is reset.
        */
        self.filter = function(field, value) {
            var fieldmap = {};
            if (field && value) {
                fieldmap[field] = value;
            }

            var url = self.build_url(fieldmap);

            self.load(url);
        };

        // public functions
        return {
            'filter': self.filter
        };
    };

    /*
        If a function is wrapped with the acquire_lock it cannot be called
        again as long as it is running.

        It stops this function from repeating forever:

        var infinite = function() {
            infinite();
        }
        infinite();

        By wrapping it:

        var infinite = function acquire_lock('infinite-lock', function() {
            infinite(); // will lead nowhere
        })
        infinite();

        The use for this function is to wrap event-handlers so they can change
        things on the dom without triggering another invocation of themselves.
    */
    var locked = {};
    var acquire_lock = function(id, inner_function) {
        if (! _.has(locked, id)) {
            locked[id] = false;
        }
        return function() {
            if (locked[id]) return;
            try {
                locked[id] = true;
                return inner_function.apply(this, arguments);
            } finally {
                locked[id] = false;
            }
        };
    };

    /*
        Drives the ListFilter through select elements. Each select element
        is expected to have an 'all' value with the value set to '__all__' that
        is supposed to trigger the reset of the filter. The select must also
        have a data-attribute called 'data-filter-attribute' which referes to the
        fieldname used on the ListFilter. The field-name is passed to the
        filter function when the selection changes along with the text of
        the selected option.

        An optional reset-element may be specified which triggers a reset of the
        filter if it is clicked. All options are also passed along to the
        ListFilter.

        Only one selection is ever used - they are not combined.
    */
    $.fn.ListFilterTable = function(options) {
        var table = $(this);

        options = $.extend({
            'reset-element': null,
            'select-elements': 'select'
        }, options);

        var selects = table.find(options['select-elements']);

        var list_filter = $.ListFilter(options);

        return selects.each(function() {

            var box = $(this);
            var attribute = box.data('filter-attribute');

            var self = {};

            self.selected_value = function() {
                var selected = box.find('option:selected');
                if (selected.attr('value') == '__all__') {
                    return null;
                } else {
                    return selected.text();
                }
            };

            self.change_handler = function(e) {
                var value = self.selected_value();

                if (value) {
                    list_filter.filter(attribute, value);
                } else {
                    list_filter.filter();
                }

                _.each(selects, function(other_box) {
                    if (other_box != box.get(0)) {

                        // reset the selection of the other selects to
                        // indicate that the different selections are not
                        // combined together

                        $(other_box).find('option[value="__all__"]').attr(
                            'selected', 'selected'
                        );
                    }
                });
            };

            self.reset_handler = function(e) {
                list_filter.filter();
                selects.find('option[value="__all__"]').attr(
                    'selected', 'selected'
                );
                e.preventDefault();
            };

            box.change(acquire_lock('change-box', self.change_handler));

            if (options['reset-element']) {
                var setup_handler = function() {
                    $(options['reset-element']).click(
                        acquire_lock('change-box', self.reset_handler)
                    );
                };
                $(document).on('filter-fragments-loaded', setup_handler);
            }
        });
    };
});