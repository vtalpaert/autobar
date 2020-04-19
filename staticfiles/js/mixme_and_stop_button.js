var switched_to_stop_button = false;
function switch_to_stop_button(div_id) {
  $(div_id).prop('disabled', true);
  $("#modal-close-button").prop('disabled', true);
  switched_to_stop_button = true;
  setTimeout(function() {
    $(div_id).removeClass("btn-primary");
    $(div_id).addClass("btn-danger");
    $(div_id).html('STOP');
    $(div_id).prop('disabled', false);
  }, 2000);
}

function start_animation() {
  var video = document.getElementById('animation');
  video.play();
}

function set_mixme_and_stop_button(div_id, mix_id, csrf_token, error_div_id) {
  $(div_id).on('click', function(e){
    e.preventDefault();
    if (switched_to_stop_button) {
        $.ajax({
          type: 'POST',
          url:"/hardware/emergencystop",
          data: {
            csrfmiddlewaretoken: csrf_token,
          },
          success: function(response){
            $(div_id).prop('disabled', true);
            $(div_id).html('STOPPED');
            setTimeout(function() {
              $('#modal').modal('hide')
            }, 2000); /* redundant with report hardware state */
          },
          error: function(error) {
            console.log(error);
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
          if (response['accepted']) {
            switch_to_stop_button(div_id);
            start_animation();
            continuous_check_order(response['order_id'], 500);
          };
        },
        error: function(error) {
          console.log(error);
          $(error_div_id).html(error.responseText);
        }
      });
    }
  });
}
