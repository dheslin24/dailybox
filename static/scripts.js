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
