const aws = require("aws-sdk");

module.exports.index = function (event, context) {
  try {
    const ec2 = new aws.EC2({ region: "us-east-1" });
    ec2.describeInstances(
      {
        Filters: [
          {
            Name: "tag:aws:ec2launchtemplate:id",
            Values: ["lt-068610880f56280b5"],
          },
        ],
      },
      (err, data) => {
        if (err) throw err;

        for (const r of data.Reservations) {
          for (const i of r.Instances) {
            const instanceId = i.InstanceId;
            console.log(`Terminating ${instanceId}`);

            ec2.terminateInstances(
              {
                InstanceIds: [instanceId],
              },
              (err, data) => {
                if (err) throw err;
                console.log(data);
              }
            );
          }
        }
      }
    );
  } catch (err) {
    console.log("There was an error");
    console.log(err);
  }
};
