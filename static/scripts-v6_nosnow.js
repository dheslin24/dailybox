//function myMove() {
//  var elem = document.getElementById("myAnimation");
//  var pos = 0;
//  var id = setInterval(frame, 10);
//  function frame() {
//    if (pos == 350) {
//      clearInterval(id);
//    } else {
//      pos++;
//      elem.style.top = pos + 'px';
//      elem.style.left = pos + 'px';
//    }
//  }
//}

function empty()
{
    var empt = document.getElementById("rand").value;
    console.log(empt);
    console.log("got to empt");
    if (empt == "")
    {
       alert("Please enter # of boxes");
       return false;
    }
       return true;
}
