function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function set_state_html(text) {
    $("#hardware-state").html(text);
}

function change_hardware_color(prev, next) {
    $("#hardware-state").removeClass(prev);
    $("#hardware-state").addClass(next);
}

function show_hardware_state() {
    $.ajax({
        type: 'GET',
        url:"/hardware/info",
        success: function(response){
            set_state_html(response['state_verbose']);
        },
        error: function(error) {
            console.log(error);
            $("#modal").html(error.responseText);
        }
    });
}

function display_order_state(response) {
    if (response['accepted']) {
        set_state_html(response['status_verbose']);
        if (response['done']) {
            change_hardware_color("btn-secondary", "btn-success");
            setTimeout(function() {
                $('#modal').modal('hide')
              }, 2000);
        }
    } else {
        set_state_html('Order was refused');
        change_hardware_color("btn-secondary", "btn-danger");
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
            console.log(error);
            $("#modal").html(error.responseText);
        }
    });
}
