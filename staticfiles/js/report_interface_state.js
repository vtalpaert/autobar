function set_state(text) {
    $("#interface-state").html(text);
}

function interface_color(prev, next) {
    $("#interface-state").removeClass(prev);
    $("#interface-state").addClass(next);
}

function interface_state() {
    $.ajax({
        type: 'GET',
        url:"/hardware/interface",
        success: function(response){
            console.log(response);
            set_state(response['state_verbose']);
        },
        error: function(error) {
            $("#modal").html(error.responseText);
        }
    });
}

function order_state(response) {
    if (response['accepted']) {
        set_state(response['status_verbose']);
        if (response['status_verbose'] == 'Done') {
            interface_color("btn-secondary", "btn-success");
        }
    } else {
        set_state('Order was refused');
        interface_color("btn-secondary", "btn-danger");
    }
}

function check_order(order_id) {
    $.ajax({
        type: 'GET',
        url:"/order/check/" + order_id,
        success: function(response){
            console.log(response);
            order_state(response);
        },
        error: function(error) {
            $("#modal").html(error.responseText);
        }
    });
}