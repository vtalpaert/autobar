var switched_to_stop_button = false;
function switch_to_stop_button(div_id) {
  $(div_id).prop('disabled', true);
  switched_to_stop_button = true;
  setTimeout(function() {
    $(div_id).removeClass("btn-primary");
    $(div_id).addClass("btn-danger");
    $(div_id).html('STOP');
    $(div_id).prop('disabled', false);
  }, 2000);
}

function set_mixme_and_stop_button(div_id, mix_id, csrf_token, error_div_id) {
  $(div_id).on('click', function(e){
    e.preventDefault();
    if (switched_to_stop_button) {
        $.ajax({
          type: 'POST',
          url:"/hardware/interface/stop",
          data: {
            csrfmiddlewaretoken: csrf_token,
          },
          success: function(response){
            $(div_id).prop('disabled', true);
            $(div_id).html('STOPPED');
          },
          error: function(error) {
            $(error_div_id).html(error.responseText);
          }
      });
    } else {
      $.ajax({
        type: 'POST',
        url:"/order/create/" + mix_id,
        data: {
          csrfmiddlewaretoken: csrf_token,
        },
        success: function(response){
          display_order_state(response);
          switch_to_stop_button(div_id);
          continuous_check_order(response['order_id'], 500);
        },
        error: function(error) {
          $(error_div_id).html(error.responseText);
        }
      });
    }
  });
}
