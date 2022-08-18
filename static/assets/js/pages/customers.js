$(document).ready((e) => {
  document.querySelector("a.nav-link.active").classList.remove("active");
  document.querySelectorAll("a.nav-link")[1].classList.add("active");
  console.log("JQuery available");
  fillCustomers();
  setTimeout(() => {
    document.querySelectorAll("a.delete").forEach((el) => {
      el.addEventListener("click", (t) => {
        let row = el.parentElement.parentElement.parentElement.parentElement;
        axios
          .post(`/api/v1/customer/delete/${row.id}`)
          .then((res) => {
            console.log(res.data.message);
            row.remove();
          })
          .catch((err) => console.log(err));
      });
    });
    document.querySelectorAll("a.update").forEach((el) => {
      el.addEventListener("click", (t) => {
        let row = el.parentElement.parentElement.parentElement.parentElement;
        axios
          .get(`/api/v1/customer/${row.id}`)
          .then((res) => {
            let f = document.querySelector("form#updateCustomerModalForm");
            f.querySelector("input#ref").value = row.id;
            document.querySelector("span#customer-to-update").textContent =
              res.data.data.name;
            f.querySelectorAll("input").forEach((el) => {
              if (el.getAttribute("type") != "checkbox") {
                el.value = res.data.data[el.name];
                if (el.name == "city") {
                  el.value = res.data.data["city"]["name"];
                }
              } else {
                el.checked = res.data.data[el.name];
              }
            });
          })
          .catch((err) => console.log(err));
      });
      /*
      axios
        .get(`/api/customers/${_id}`)
        .then((res) => {
          let f = document.querySelector("form#updateCustomerModalForm");
          document.querySelector("span#customer-to-update").textContent =
            res.data.data.name;
          f.querySelectorAll("input").forEach((el) => {
            el.value = res.data.data[el.name];
            if (el.name == "city") {
              el.value = res.data.data["city"]["name"];
            }
          });
        })
        .catch((err) => console.log(err));
      */
    });
  }, 1000);
});

function fillCustomers() {
  let table = document.querySelector("tbody#customersTbody");
  axios
    .get("/api/v1/customers")
    .then((res) => {
      if (res.data.success) {
        table?.querySelectorAll("tr").forEach((el) => {
          el.remove();
        });

        res.data.data.forEach((element) => {
          table?.appendChild(createRow(element));
        });
      }
    })
    .catch((err) => console.log(err));
}

function createRow(data) {
  let row = document.createElement("tr");
  row.id = data.pk;
  row.innerHTML = `
    <td>
        <div class="d-flex px-2 py-1">
        <div>
            <img
            src="/static/media/img/${
              data.statut == "R" ? "particulier.png" : "entreprise.png"
            }"
            class="avatar avatar-sm me-3"
            alt="user3"
            />
        </div>
        <div class="d-flex flex-column justify-content-center">
            <h6 class="mb-0 text-sm" data-bs-toggle="modal" data-bs-target="#customerDetailModal">${
              data.name.length > 30
                ? data.name.slice(0, 30) + " ..."
                : data.name
            }</h6>
            <p class="text-xs text-secondary mb-0">
            ${data.email}
            </p>
        </div>
        </div>
    </td>
    <td>
        <p class="text-xs font-weight-bold mb-0">${data.city.name}</p>
        <p class="text-xs text-secondary mb-0">${data.province}</p>
    </td>
    <td class="align-middle text-center text-sm">
        <span class="badge badge-sm ${
          data.is_prospect ? "bg-gradient-secondary" : "bg-gradient-success"
        }"
        >${data.is_regulier ? "Régulier" : "Irrégulier"}</span>
    </td>
    <td class="align-middle text-center">
        <span class="text-secondary text-xs font-weight-bold"
        >${data.joined}</span
        >
    </td>
    <td class="align-middle text-center">
        <a
            href="javascript:;"
            class="nav-link text-body p-0"
            id="dropdownCustomerMenuButton-${data.pk}"
            data-bs-toggle="dropdown"
            aria-expanded="false"
        >
            <i class="fa fa-ellipsis-h cursor-pointer"></i>
        </a>
        <ul
            class="dropdown-menu dropdown-menu-end px-2 py-3 me-sm-n4"
            aria-labelledby="dropdownCustomerMenuButton-${data.pk}"
        >
            <li class="mb-2">
            <a class="dropdown-item border-radius-md update" data-bs-toggle="modal" data-bs-target="#updateCustomerModal">
                <p class="font-weight-bold">Modifier ce client</p>
            </a>
            </li>
            <li class="mb-2">
            <a class="dropdown-item border-radius-md disabled">
                <p class="font-weight-bold">Facturer son pack</p>
            </a>
            </li>
            <li class="mb-2">
            <a class="dropdown-item border-radius-md delete">
                <p class="font-weight-bold">Supprimer ce client</p>
            </a>
            </li>
        </ul>
    </td>
  `;

  return row;
}

document
  .querySelector("form#addCustomerModalForm")
  ?.addEventListener("submit", (e) => {
    e.preventDefault();
    let data = new FormData(e.target);
    axios
      .post("/api/v1/customer/create", data)
      .then((res) => {
        showModalAlert("addCustomerModal", res);
        if (res.data.success) {
          let row = createRow(res.data.data);
          document.querySelector("tbody#customersTbody").prepend(row);
          e.target.reset();
        }
      })
      .catch((err) => console.log(err));
  });

document
  .querySelector("form#updateCustomerModalForm")
  ?.addEventListener("submit", (e) => {
    e.preventDefault();
    let data = new FormData(e.target);
    let pk = data.get("pk");
    data.delete("pk");
    axios
      .post(`/api/v1/customer/update/${pk}`, data)
      .then((res) => {
        showModalAlert("updateCustomerModal", res);
      })
      .catch((err) => console.log(err));

    console.log(data);
  });