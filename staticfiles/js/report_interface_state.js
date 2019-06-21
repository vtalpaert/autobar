function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function set_state_html(text) {
    $("#interface-state").html(text);
}

function change_interface_color(prev, next) {
    $("#interface-state").removeClass(prev);
    $("#interface-state").addClass(next);
}

function show_interface_state() {
    $.ajax({
        type: 'GET',
        url:"/hardware/interface",
        success: function(response){
            set_state_html(response['state_verbose']);
        },
        error: function(error) {
            $("#modal").html(error.responseText);
        }
    });
}

function display_order_state(response) {
    if (response['accepted']) {
        set_state_html(response['status_verbose']);
        if (response['done']) {
            change_interface_color("btn-secondary", "btn-success");
        }
    } else {
        set_state_html('Order was refused');
        change_interface_color("btn-secondary", "btn-danger");
    }
}

function continuous_check_order(order_id, max_try) {
    $.ajax({
        type: 'GET',
        url:"/order/check/" + order_id,
        success: async function(response){
            display_order_state(response);
            if (!response['done'] && max_try > 0) {
                await sleep(100);
                continuous_check_order(order_id, max_try - 1);
            }
        },
        error: function(error) {
            $("#modal").html(error.responseText);
        }
    });
}
