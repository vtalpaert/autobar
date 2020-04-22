
function start_animation() {
  var video = document.getElementById('animation');
  video.play();
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function set_info_bubble_html(text) {
  $("#info-bubble").html(text);
}

function change_info_bubble_color(prev, next) {
  $("#info-bubble").removeClass(prev);
  $("#info-bubble").addClass(next);
}

function update_order_state(response) {
  set_info_bubble_html(response['status_verbose']);
  if (response['done']) {
    change_info_bubble_color("btn-secondary", response['btn']); /* btn-success or btn-danger */
    setTimeout(function() {
        $('#modal').modal('hide')
    }, 2000);
  }
}

function continuous_check_order(order_id, max_try) {
  $.ajax({
    type: 'GET',
    url:"/order/check/" + order_id,
    success: async function(response){
      update_order_state(response);
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
          }, 2000); /* redundant with update_order_state */
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
          if (response['accepted']) {
            switch_to_stop_button(div_id);
            start_animation();
            continuous_check_order(response['order_id'], 500);
          } else {
            set_info_bubble_html('Order was refused');
            change_info_bubble_color("btn-secondary", "btn-danger");
          }
        },
        error: function(error) {
          console.log(error);
          $(error_div_id).html(error.responseText);
        }
      });
    }
  });
}
