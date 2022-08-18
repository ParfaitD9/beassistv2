function showModalAlert(modalId, res) {
  let modal = document.getElementById(modalId);
  let msg = modal.querySelector("div.alert");
  msg.querySelector("p").textContent = "";
  if (res.data.success) {
    msg.classList.remove("alert-danger");
    msg.classList.add("alert-success");
  } else {
    msg.classList.remove("alert-success");
    msg.classList.add("alert-danger");
    console.log(res.data.message);
  }
  msg.querySelector("p").textContent = `${res.data.message}`;
}

function load_customers() {
  let select = document.querySelector("select#customers");
  if (select) {
    axios
      .get("/api/v1/customers")
      .then((res) => {
        res.data.data.forEach((cus) => {
          let opt = document.createElement("option");
          opt.value = cus.pk;
          opt.text = cus.name;
          select.appendChild(opt);
        });
      })
      .catch((err) => console.log(err));
  }
}

function load_subtasks() {
  let dt = document.querySelector("datalist#subtasks");
  if (dt) {
    axios
      .get("/api/v1/subtasks")
      .then((res) => {
        res.data.data.forEach((sub) => {
          let opt = document.createElement("option");
          opt.text = sub.name;
          dt.appendChild(opt);
        });
      })
      .catch((err) => console.log(err));
  }
}

function load_packs() {
  let dt = document.querySelector("select#packs");
  if (dt) {
    axios
      .get("/api/v1/packs")
      .then((res) => {
        res.data.data.forEach((sub) => {
          let opt = document.createElement("option");
          opt.text = sub.name + ` ${sub.customer.name.slice(0, 17)}`;
          opt.value = sub.pk;
          dt.appendChild(opt);
        });
      })
      .catch((err) => console.log(err));
  }
}
