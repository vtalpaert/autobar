// all like related functions
var liked = false;
function like_onclick(div_id, mix_id, csrf_token, error_div)
{
    if (liked) {
        liked = false;
        $(div_id)[0].style.fill = "";
    } else {
        liked = true;
        $(div_id)[0].style.fill = "dodgerblue";
    }
    $.ajax({
        type: 'POST',
        url: '/mix/like/' + mix_id,
        data: {
            csrfmiddlewaretoken: csrf_token,
            like: liked
        },
        error: function(error) {
            $(error_div).html(error.responseText);
        }
    });
}
